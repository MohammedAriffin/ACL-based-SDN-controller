from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp

class ACLController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ACLController, self).__init__(*args, **kwargs)
        self.student_prefix = "10.0.1."
        self.guest_prefix = "10.0.2."
        self.admin_ip = "10.0.10.10"

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        # table-miss: send to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.add_flow(dp, priority=0, match=match, actions=actions)
        self.logger.info("Table-miss installed on dpid=%s", dp.id)

    def add_flow(self, dp, priority, match, actions, idle=60, hard=0):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=priority,
                                idle_timeout=idle, hard_timeout=hard,
                                match=match, instructions=inst)
        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        ip4 = pkt.get_protocol(ipv4.ipv4)
        if not ip4:
            # Non-IPv4: flood first packet
            actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
            out = parser.OFPPacketOut(datapath=dp, buffer_id=ofp.OFP_NO_BUFFER,
                                    in_port=msg.match['in_port'],
                                    actions=actions, data=msg.data)
            dp.send_msg(out)
            return

        src, dst, proto = ip4.src, ip4.dst, ip4.proto
        tcp_hdr = pkt.get_protocol(tcp.tcp)
        udp_hdr = pkt.get_protocol(udp.udp)
        dport = tcp_hdr.dst_port if tcp_hdr else (udp_hdr.dst_port if udp_hdr else None)

        # Block ICMP (ping) from Host A (10.0.1.10) to Host B (10.0.1.11)
        if proto == 1 and src == "10.0.1.10" and dst == "10.0.1.11":
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src, ipv4_dst=dst, ip_proto=1)
            self.add_flow(dp, priority=200, match=match, actions=[])
            return

        # Deny student → admin (all)
        if src.startswith(self.student_prefix) and dst == self.admin_ip:
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src, ipv4_dst=dst)
            self.add_flow(dp, priority=110, match=match, actions=[])
            return

        # Guest policy: allow HTTP(80), deny FTP(21)/SSH(22), else deny
        if src.startswith(self.guest_prefix):
            if proto == 6 and dport == 80:
                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src, ipv4_dst=dst, ip_proto=6, tcp_dst=80)
                actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
                self.add_flow(dp, priority=100, match=match, actions=actions)
                return
            if proto == 6 and dport in (21, 22):
                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src, ipv4_dst=dst, ip_proto=6, tcp_dst=dport)
                self.add_flow(dp, priority=120, match=match, actions=[])
                return
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src, ipv4_dst=dst)
            self.add_flow(dp, priority=10, match=match, actions=[])
            return

        # Fallback: flood first packet (can be tightened later)
        actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
        out = parser.OFPPacketOut(datapath=dp, buffer_id=ofp.OFP_NO_BUFFER,
                                in_port=msg.match['in_port'], actions=actions, data=msg.data)
        dp.send_msg(out)