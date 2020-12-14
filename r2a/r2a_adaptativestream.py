import time
from r2a.ir2a import IR2A
from player.parser import *
from math import exp

class R2A_AdaptativeStream(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        # Real throughput of the segments
        self.tpSegment_list = []

        # Estimated throughput of the segments
        self.tpEstimated_list = []
        self.request_time = 0
        self.qi_list = []
        self.segment_idx = 0
        self.ideal_buffer = 20


    def __get_delta__(self):

        estimated_throughput = self.tpEstimated_list[len(self.tpEstimated_list) - 1]
        real_throughput = self.tpSegment_list[len(self.tpSegment_list) - 1]

        # if(len(self.tpEstimated_list) == len(self.tpSegment_list)):
        #     print("TA IGUAL, NICE JDAUSHDASUHDASUDHAS\n\n\n\n\n")

        # else:
        #     print("TA ERRADO LUL \n\n\n\n\n")

        my_p = abs(real_throughput - estimated_throughput) / estimated_throughput
        
        # Theses two values depends on the type of the network used.
        # Assuming the net used as a wireless network
        # For cabed network, use k = 10 and p_0 = 0.05 
        k = 6; p_0 = 0.2

        myDelta = 1 / (1 + exp(-k * (my_p - p_0)))

        print(f"P is {my_p}.")
        
        return myDelta

    def __get_quality_index__(self):
        qi_idx = 0
        # estimated_tp = 0
        idx = len(self.tpEstimated_list) - 1

        estimated_tp = self.tpEstimated_list[idx]
        i = 0

        # print("\n\n////////////////////")
        # print(f"Seu indice = {idx}, tam de tpSegment = {len(self.tpEstimated_list)}")
        # print(f"{estimated_tp}")
        # print("//////////////////////\n\n")

        while(i < len(self.qi_list)):
            if(self.qi_list[i] < estimated_tp):
                qi_idx = i
            else:
                break

            i += 1

        return qi_idx    

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter() # For the real throughput calculus 
        self.send_down(msg)
    
    def handle_xml_response(self, msg):
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi_list = parsed_mpd.get_qi()

        t = time.perf_counter() - self.request_time

        # estimated_initial_segment_throughput = self.qi_list[0]

        # self.tpSegment_list.append(initial_segment_throughput)
        # self.tpEstimated_list.append(estimated_initial_segment_throughput)

        self.send_up(msg)
    
    def handle_segment_size_request(self, msg):

        self.request_time = time.perf_counter() # For the real throughput calculus
        qi_idx = 0; delta = 0.0
        buffer_size = (0,0,None)

        # print(f"\n\n\n\n\nalo {type(buffer_size)}\n\n\n\n")
        
        if(self.segment_idx == 0):
            self.tpEstimated_list.append(self.qi_list[0])
            qi_idx = self.__get_quality_index__()
            self.segment_idx += 1

        elif(self.segment_idx <= 2):
 
            estimated_tp_idx = len(self.tpSegment_list) - 1
            self.tpEstimated_list.append(self.tpSegment_list[estimated_tp_idx])
            qi_idx = self.__get_quality_index__()
            self.segment_idx += 1

        else:
            delta = self.__get_delta__()
            self.segment_idx += 1

            # The penult estimated throughput index 
            pt_idx = len(self.tpEstimated_list) - 2
            # The last real throughput index
            lt_idx = len(self.tpSegment_list) - 1

            estimated_throughput = (1 - delta) * self.tpEstimated_list[pt_idx] + delta * self.tpSegment_list[lt_idx]

            buffer_size = self.whiteboard.get_playback_buffer_size()[-1][-1]

            # Putting a security margin in case the buffer is to low
            if(buffer_size < self.ideal_buffer):
                estimated_throughput = 0.6 * estimated_throughput
                
            self.tpEstimated_list.append(estimated_throughput)

            qi_idx = self.__get_quality_index__()
        
        msg.add_quality_id(self.qi_list[qi_idx])

        print("-----------------------------------------------------")
        print(f"Your qi: {qi_idx}, your delta: {delta}, seg_idx: {self.segment_idx - 1}")
        print(f"Seu buffer: {buffer_size}")
        # print(self.qi_list)
        print(self.tpEstimated_list[-5:-1])
        print("-----------------------------------------------------\n")

        self.send_down(msg)
    
    def handle_segment_size_response(self, msg):

        msg_size = msg.get_bit_length()

        # print(f"\n\n\n\n\n\n{msg_size} salve\n\n\n\n\n\n\n\n")

        t = (time.perf_counter() - self.request_time)
        real_throughput = msg_size / t

        self.tpSegment_list.append(real_throughput)
        print(self.tpSegment_list[-5:-1])
        self.send_up(msg)
    
    def initialize(self):
        pass
    
    def finalization(self):
        pass