import socket
import struct
import threading
import time

class PortScanner:
    """Port Scanner using TCP model"""
    def __init__(self, port_list):
        """init port set"""
        self.port_list = port_list
        self.source_ip = '192.168.152.129'
        self.source_port = 38060
        self.MAXSIZE = 1500
        self.timelimit = 0.2
        self.MAXLOOP = 10

    def scan(self, host):
        """Ports scanning"""
        # wait for syn ack from {host}
        host_sep = host.split(sep='.')
        # if host is not a ip addr but a domain name
        if(len(host_sep) != 4):
            try:
                host = socket.gethostbyname(host)
            except Exception as e:
                print(e)                # print the error message
                return 
        start_time = time.time()
        # a subthread waits for syn from scanning port
        thread = threading.Thread(target=self.wait_for_syn, args=(host, ))
        thread.start()
        loop = 0
        # send syn continuously until loop to the MAXLOOP or all ports response
        while loop < self.MAXLOOP and len(self.port_list):
            # send syn to each port of {host}
            for port in self.port_list:
                time.sleep(0.5)
                self.send_syn(self.source_ip, self.source_port, host, port)
            loop += 1
        end_time = time.time()
        print('{0} Scanning costs {1} seconds'.format(host, end_time - start_time))

    def wait_for_syn(self, host):
        while len(self.port_list):
            self.recv_syn(host)

    def bind(self, ip, port):
        self.source_ip = ip
        self.source_port = port

    def send_syn(self, source_ip, source_port, dest_ip, dest_port):
        """send syn package"""
        sk = self.make_socket()
        ip_header = self.make_ip_header(source_ip, dest_ip)
        tcp_header = self.make_tcp_syn_header(source_ip, source_port, dest_ip, dest_port)
        package_syn = ip_header + tcp_header    # no data
        sk.sendto(package_syn, (dest_ip, dest_port))
    
    def send_fin(self, source_ip, source_port, dest_ip, dest_port):
        """send fin package"""
        sk = self.make_socket()
        ip_header = self.make_ip_header(source_ip, dest_ip)
        tcp_fin_header = self.make_tcp_fin_header(source_ip, source_port, dest_ip, dest_port)
        package_fin = ip_header + tcp_fin_header
        sk.sendto(package_fin, (dest_ip, dest_port))

    def recv_syn(self, host):
        """receive syn from {host}"""
        sk = self.make_socket()
        try:
            message, addr = sk.recvfrom(self.MAXSIZE)
        except socket.timeout:
            # print('timeout')
            return False
        # check syn flag, ack flag and ip addr
        source_ip = message[12:16]
        source_port = (message[20] << 8) + message[21]
        dest_ip = message[16:20]
        dest_port = (message[22] << 8) + message[23]
        # print(socket.inet_ntoa(source_ip), source_port)
        # print(socket.inet_ntoa(dest_ip), dest_port)
        if source_port in self.port_list:
            self.port_list.remove(source_port)
            if message[33] & 0x12 == 0x12:
                print("Receive a syn message from (Host {0} port {1}) ".format(socket.inet_ntoa(source_ip), source_port))
                self.send_fin(self.source_ip, self.source_port, host, source_port)
                return True
            elif message[33] & 0x4 == 0x4:
                print('(Host {0} port {1}) has closed the connection'.format(socket.inet_ntoa(source_ip), source_port))
                return True
        return False

    def make_tcp_syn_header(self, source_ip, source_port, dest_ip, dest_port):
        """return a syn header of the tcp segment"""
        # fill the TCP segment part
        tcp_sport = source_port
        tcp_dport = dest_port
        tcp_seq = 0
        tcp_ack = 0
        tcp_off = 5    # 5 * 4 = 20 bytes
        tcp_res = 0
        tcp_off_res = (tcp_off << 4) + tcp_res
        # flags
        urg = 0
        ack = 0
        psh = 0
        rst = 0
        syn = 1
        fin = 0
        # combine
        tcp_flags = (urg << 5) + (ack << 4) + (psh << 3) + (rst << 2) + (syn << 1) + (fin)
        tcp_win = socket.htons(9999)
        tcp_sum = 0
        tcp_urp = 0
        # sum unchecked
        tcp_header = struct.pack('!HHLLBBHHH', tcp_sport, tcp_dport, tcp_seq, tcp_ack, tcp_off_res, tcp_flags, tcp_win, tcp_sum, tcp_urp)
        # pseudo header
        ip_saddr = socket.inet_aton(source_ip)
        ip_daddr = socket.inet_aton(dest_ip)
        zero = 0
        protocol = socket.IPPROTO_TCP
        tcp_length = len(tcp_header)
        pseudo_header = struct.pack('!4s4sBBH', ip_saddr, ip_daddr, zero, protocol, tcp_length)
        tcp_sum = self.checksum(pseudo_header + tcp_header)
        # repack
        tcp_header = struct.pack('!HHLLBBHHH', tcp_sport, tcp_dport, tcp_seq, tcp_ack, tcp_off_res, tcp_flags, tcp_win, tcp_sum, tcp_urp)
        return tcp_header

    def make_tcp_fin_header(self, source_ip, source_port, dest_ip, dest_port):
        """return a fin header of the tcp segment"""
        tcp_sport = source_port
        tcp_dport = dest_port
        tcp_seq = 0
        tcp_ack = 0
        tcp_off = 5    # 5 * 4 = 20 bytes
        tcp_res = 0
        tcp_off_res = (tcp_off << 4) + tcp_res
        # flags
        urg = 0
        ack = 0
        psh = 0
        rst = 0
        syn = 0
        fin = 1
        # combine
        tcp_flags = (urg << 5) + (ack << 4) + (psh << 3) + (rst << 2) + (syn << 1) + (fin)
        tcp_win = socket.htons(9999)
        tcp_sum = 0
        tcp_urp = 0
        # sum unchecked
        tcp_header = struct.pack('!HHLLBBHHH', tcp_sport, tcp_dport, tcp_seq, tcp_ack, tcp_off_res, tcp_flags, tcp_win, tcp_sum, tcp_urp)
        # pseudo header
        ip_saddr = socket.inet_aton(source_ip)
        ip_daddr = socket.inet_aton(dest_ip)
        zero = 0
        protocol = socket.IPPROTO_TCP
        tcp_length = len(tcp_header)
        pseudo_header = struct.pack('!4s4sBBH', ip_saddr, ip_daddr, zero, protocol, tcp_length)
        tcp_sum = self.checksum(pseudo_header + tcp_header)
        # repack
        tcp_header = struct.pack('!HHLLBBHHH', tcp_sport, tcp_dport, tcp_seq, tcp_ack, tcp_off_res, tcp_flags, tcp_win, tcp_sum, tcp_urp)
        return tcp_header


    def make_ip_header(self, source_ip, dest_ip):
        """return a header of the ip segment"""
        # fill the IP segment part
        version = 0x4
        ip_hl = 5   # 5 * 4 = 20 bytes
        ip_ver_hl = (version << 4) + ip_hl
        ip_tos = 0
        ip_tl = 40
        ip_id = 0
        ip_offset = 0
        ip_ttl = 255
        ip_proto = socket.IPPROTO_TCP
        ip_sum = 0
        # pack the fields
        ip_saddr = socket.inet_aton(source_ip)
        ip_daddr = socket.inet_aton(dest_ip)
        ip_header = struct.pack('!BBHHHBBH4s4s', ip_ver_hl, ip_tos, ip_tl, ip_id, ip_offset, ip_ttl, ip_proto, ip_sum, ip_saddr, ip_daddr)
        ip_sum =  self.checksum(ip_header)
        # calc the checksum and repack the fields
        ip_header = struct.pack('!BBHHHBBH4s4s', ip_ver_hl, ip_tos, ip_tl, ip_id, ip_offset, ip_ttl, ip_proto, ip_sum, ip_saddr, ip_daddr)
        return ip_header

    def checksum(self, data):
        """calculate the checksum of the tcp header"""
        s = 0
        isOdd = len(data) % 2
        for i in range(0, len(data) - isOdd, 2):
            s += (data[i] << 8) + data[i+1]
        if isOdd:
            s += data[i+1]
        while (s >> 16):
            s = (s & 0xFFFF) + (s >> 16)
        s = ~s & 0xffff
        return s

    def make_socket(self):
        """return a socket using RAW"""
        sk = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP) # set type SOCK_RAW
        sk.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sk.setblocking(1)
        sk.settimeout(self.timelimit)
        sk.bind((self.source_ip, self.source_port))
        return sk

        
def test():
    # port_list = [1,3,6,9,13,17,19,20,21,22,23,24,25,30,32,37,42,49,53,70,79,80,81,82,83,84,88,89,99,106,109,110,113,119,125,135,139,143,146,161,163,179,199,211,222,254,255,259,264,280,301,306,311,340,366,389,406,416,425,427,443,444,458,464,481,497,500,512,513,514,524,541,543,544,548,554,563,587,593,616,625,631,636,646,648,666,667,683,687,691,700,705,711,714,720,722,726,749,765,777,783,787,800,808,843,873,880,888,898,900,901,902,911,981,987,990,992,995,999,1000,1001,1007,1009,1010,1021,1022,1023,1024,1025,1026,1027,1028,1029,1030,1031,1032,1033,1034,1035,1036,1037,1038,1039,1040,1041,1042,1043,1044,1045,1046,1047,1048,1049,1050,1051,1052,1053,1054,1055,1056,1057,1058,1059,1060,1061,1062,1063,1064,1065,1066,1067,1068,1069,1070,1071,1072,1073,1074,1075,1076,1077,1078,1079,1080,1081,1082,1083,1084,1085,1086,1087,1088,1089,1090,1091,1092,1093,1094,1095,1096,1097,1098,1099,1102,1104,1105,1106,1107,1110,1111,1112,1113,1117,1119,1121,1122,1123,1126,1130,1131,1137,1141,1145,1147,1148,1151,1154,1163,1164,1165,1169,1174,1183,1185,1186,1192,1198,1201,1213,1216,1217,1233,1236,1244,1247,1259,1271,1277,1287,1296,1300,1309,1310,1322,1328,1334,1352,1417,1433,1443,1455,1461,1494,1500,1503,1521,1524,1533,1556,1580,1583,1594,1600,1641,1658,1666,1687,1700,1717,1718,1719,1720,1723,1755,1761,1782,1801,1805,1812,1839,1862,1863,1875,1900,1914,1935,1947,1971,1974,1984,1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2013,2020,2021,2030,2033,2034,2038,2040,2041,2042,2045,2046,2047,2048,2065,2068,2099,2103,2105,2106,2111,2119,2121,2126,2135,2144,2160,2170,2179,2190,2196,2200,2222,2251,2260,2288,2301,2323,2366,2381,2382,2393,2399,2401,2492,2500,2522,2525,2557,2601,2604,2607,2638,2701,2710,2717,2725,2800,2809,2811,2869,2875,2909,2920,2967,2998,3000,3003,3005,3006,3011,3013,3017,3030,3052,3071,3077,3128,3168,3211,3221,3260,3268,3283,3300,3306,3322,3323,3324,3333,3351,3367,3369,3370,3371,3389,3404,3476,3493,3517,3527,3546,3551,3580,3659,3689,3703,3737,3766,3784,3800,3809,3814,3826,3827,3851,3869,3871,3878,3880,3889,3905,3914,3918,3920,3945,3971,3986,3995,3998,4000,4001,4002,4003,4004,4005,4045,4111,4125,4129,4224,4242,4279,4321,4343,4443,4444,4445,4449,4550,4567,4662,4848,4899,4998,5000,5001,5002,5003,5009,5030,5033,5050,5054,5060,5080,5087,5100,5101,5120,5190,5200,5214,5221,5225,5269,5280,5298,5357,5405,5414,5431,5440,5500,5510,5544,5550,5555,5560,5566,5631,5633,5666,5678,5718,5730,5800,5801,5810,5815,5822,5825,5850,5859,5862,5877,5900,5901,5902,5903,5906,5910,5915,5922,5925,5950,5952,5959,5960,5961,5962,5987,5988,5998,5999,6000,6001,6002,6003,6004,6005,6006,6009,6025,6059,6100,6106,6112,6123,6129,6156,6346,6389,6502,6510,6543,6547,6565,6566,6580,6646,6666,6667,6668,6689,6692,6699,6779,6788,6792,6839,6881,6901,6969,7000,7001,7004,7007,7019,7025,7070,7100,7103,7106,7200,7402,7435,7443,7496,7512,7625,7627,7676,7741,7777,7800,7911,7920,7937,7999,8000,8001,8007,8008,8009,8010,8021,8031,8042,8045,8080,8081,8082,8083,8084,8085,8086,8087,8088,8089,8093,8099,8180,8192,8193,8200,8222,8254,8290,8291,8300,8333,8383,8400,8402,8443,8500,8600,8649,8651,8654,8701,8800,8873,8888,8899,8994,9000,9001,9002,9009,9010,9040,9050,9071,9080,9090,9099,9100,9101,9102,9110,9200,9207,9220,9290,9415,9418,9485,9500,9502,9535,9575,9593,9594,9618,9666,9876,9877,9898,9900,9917,9929,9943,9968,9998,9999,10000,10001,10002,10003,10009,10012,10024,10082,10180,10215,10243,10566,10616,10621,10626,10628,10778,11110,11967,12000,12174,12265,12345,13456,13722,13782,14000,14238,14441,15000,15002,15003,15660,15742,16000,16012,16016,16018,16080,16113,16992,17877,17988,18040,18101,18988,19101,19283,19315,19350,19780,19801,19842,20000,20005,20031,20221,20828,21571,22939,23502,24444,24800,25734,26214,27000,27352,27355,27715,28201,30000,30718,30951,31038,31337,32768,32769,32770,32771,32772,32773,32774,32775,32776,32777,32778,32779,32780,32781,32782,32783,32784,33354,33899,34571,34572,35500,38292,40193,40911,41511,42510,44176,44442,44501,45100,48080,49152,49153,49154,49155,49156,49157,49158,49159,49160,49163,49165,49167,49175,49400,49999,50000,50001,50002,50006,50300,50389,50500,50636,50800,51103,51493,52673,52822,52848,52869,54045,54328,55055,55555,55600,56737,57294,57797,58080,60020,60443,61532,61900,62078,63331,64623,64680,65000,65129,65389]
    port_list = [12001, 12002, 12004, 12008, 12010, 12012, 12018]
    print('Scan Port: {}'.format(port_list))
    port_scanner = PortScanner(port_list)
    host = '127.0.0.1'
    port_scanner.scan(host)

if __name__ == '__main__':
    test()