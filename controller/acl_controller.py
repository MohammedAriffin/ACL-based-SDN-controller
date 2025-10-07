from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp

class ACLController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ACLController, self).__init__(*args, **kwargs)
        
        # Define role-based network segments
        self.student_prefix = "10.0.1."    # Students
        self.guest_prefix = "10.0.2."      # Guests
        self.admin_prefix = "10.0.10."     # Admin subnet
        self.server_prefix = "10.0.3."     # Application servers

        # Admin server specific IP (for SSH/HTTP/FTP)
        self.admin_ip = "10.0.10.10"

        self.logger.info("ACL Controller initialized with role-based policies")

    # ----------------------------------------------------------------------
    # Switch Configuration (Table-Miss rule)
    # ----------------------------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        # Default: send unknown packets to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.add_flow(dp, priority=0, match=match, actions=actions)
        self.logger.info("Table-miss flow installed on switch %s", dp.id)

    # ----------------------------------------------------------------------
    # Utility: Flow addition
    # ----------------------------------------------------------------------
    def add_flow(self, dp, priority, match, actions, idle=60, hard=0):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=priority,
                                idle_timeout=idle, hard_timeout=hard,
                                match=match, instructions=inst)
        dp.send_msg(mod)

    # ----------------------------------------------------------------------
    # Packet-In Event Handler
    # ----------------------------------------------------------------------
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
            # Non-IPv4 traffic (ARP, etc.) -> Flood
            actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
            out = parser.OFPPacketOut(datapath=dp, buffer_id=ofp.OFP_NO_BUFFER,
                                      in_port=msg.match['in_port'], actions=actions, data=msg.data)
            dp.send_msg(out)
            return

        src, dst, proto = ip4.src, ip4.dst, ip4.proto
        tcp_hdr = pkt.get_protocol(tcp.tcp)
        udp_hdr = pkt.get_protocol(udp.udp)
        dport = tcp_hdr.dst_port if tcp_hdr else (udp_hdr.dst_port if udp_hdr else None)

        # ---------------------------------------------------------
        # ACL POLICY DEFINITIONS
        # ---------------------------------------------------------

        # 1️⃣ Block ICMP (ping) from Students to Admins
        if proto == 1 and src.startswith(self.student_prefix) and dst.startswith(self.admin_prefix):
            match = parser.OFPMatch(eth_type=0x0800, ip_proto=1, ipv4_src=src, ipv4_dst=dst)
            self.add_flow(dp, priority=300, match=match, actions=[])
            self.logger.info("Denied ICMP from Student %s → Admin %s", src, dst)
            return

        # 2️⃣ Block all access from Students to Admin subnet (default deny)
        if src.startswith(self.student_prefix) and dst.startswith(self.admin_prefix):
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src, ipv4_dst=dst)
            self.add_flow(dp, priority=250, match=match, actions=[])
            self.logger.info("Denied all traffic Student %s → Admin %s", src, dst)
            return

        # 3️⃣ Students allowed only HTTP (80) to Servers; deny others
        if src.startswith(self.student_prefix) and dst.startswith(self.server_prefix):
            if proto == 6 and dport == 80:
                match = parser.OFPMatch(eth_type=0x0800, ip_proto=6, ipv4_src=src,
                                        ipv4_dst=dst, tcp_dst=80)
                actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
                self.add_flow(dp, priority=200, match=match, actions=actions)
                self.logger.info("Allowed HTTP Student %s → Server %s", src, dst)
                return
            else:
                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src, ipv4_dst=dst)
                self.add_flow(dp, priority=180, match=match, actions=[])
                self.logger.info("Denied non-HTTP Student %s → Server %s", src, dst)
                return

        # 4️⃣ Guests allowed only HTTP (80); deny FTP (21), SSH (22), ICMP
        if src.startswith(self.guest_prefix):
            if proto == 6 and dport == 80:
                match = parser.OFPMatch(eth_type=0x0800, ip_proto=6, ipv4_src=src,
                                        ipv4_dst=dst, tcp_dst=80)
                actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
                self.add_flow(dp, priority=160, match=match, actions=actions)
                self.logger.info("Allowed HTTP Guest %s → %s", src, dst)
                return
            elif proto == 6 and dport in (21, 22):
                match = parser.OFPMatch(eth_type=0x0800, ip_proto=6, ipv4_src=src,
                                        ipv4_dst=dst, tcp_dst=dport)
                self.add_flow(dp, priority=170, match=match, actions=[])
                self.logger.info("Denied FTP/SSH Guest %s → %s", src, dst)
                return
            elif proto == 1:
                match = parser.OFPMatch(eth_type=0x0800, ip_proto=1, ipv4_src=src, ipv4_dst=dst)
                self.add_flow(dp, priority=170, match=match, actions=[])
                self.logger.info("Denied ICMP Guest %s → %s", src, dst)
                return
            else:
                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src, ipv4_dst=dst)
                self.add_flow(dp, priority=100, match=match, actions=[])
                self.logger.info("Denied unrecognized Guest %s → %s", src, dst)
                return

        # 5️⃣ Admins have full access (HTTP, SSH, ICMP allowed)
        if src.startswith(self.admin_prefix):
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src, ipv4_dst=dst)
            actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
            self.add_flow(dp, priority=140, match=match, actions=actions)
            self.logger.info("Allowed all Admin %s → %s", src, dst)
            return

        # ---------------------------------------------------------
        # Fallback rule: flood first packet (unknown flow)
        # ---------------------------------------------------------
        actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
        out = parser.OFPPacketOut(datapath=dp, buffer_id=ofp.OFP_NO_BUFFER,
                                  in_port=msg.match['in_port'], actions=actions, data=msg.data)
        dp.send_msg(out)
        self.logger.info("Fallback: Flooded %s → %s", src, dst)
