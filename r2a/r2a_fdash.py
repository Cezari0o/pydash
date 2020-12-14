from r2a.ir2a import IR2A
from player.parser import *
from math import pow, sqrt
import time
from statistics import mean

class R2A_FDash(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.last_buffer_time = 0
        self.penult_buffer_time = 0
        self.good_buffer_time = 22         # Represents the buffer in seconds
        self.throughput_segments = []
        # The list of qualitys
        self.qi_list = []
        self.last_buffer = 0
        self.buffer_back_time = self.good_buffer_time / 2

        self.request_time = 0

        self.segment_idx = 0

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()

        self.send_down(msg)

    
    def handle_xml_response(self, msg):
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi_list = parsed_mpd.get_qi()

        self.send_up(msg)

    def __get_buffering_time_degree__(self, last_bt):
        short = close = long = 0

        # if (last_bt < self.good_buffer_time):
        #     short = 1
                    
        # elif (last_bt > self.good_buffer_time * 2):
        #     long = 1
        # else:
        #     close = 1
        
        if(last_bt <= (2 * self.good_buffer_time) / 3):
            short = 1

        elif(last_bt <= self.good_buffer_time):
            short = 1 - 1 / (self.good_buffer_time / 3) * (last_bt - 2 * self.good_buffer_time /3)
            close = 1 / (self.good_buffer_time / 3) * (last_bt - 2 * self.good_buffer_time /3)
            
        elif(last_bt <= 4 * self.good_buffer_time):
            close =  1 - 1 / (3 * last_bt) * (last_bt - self.good_buffer_time)
            long  =  1 / (3 * last_bt) * (last_bt - self.good_buffer_time)

        else:
            long = 1

        return (short, close, long)
    

    def __delta_Bf_degree__(self, buffzinho):
        falling = rising = steady = 0
                
        # if (buffzinho < 0):
        #     falling = 1
        
        # elif (buffzinho > 0):
        #     rising = 1
        
        # else:
        #     steady = 1
            

        if (buffzinho <= (-2 * self.good_buffer_time) / 3):
            falling = 1
        
        elif (buffzinho > (-2 * self.good_buffer_time)/3 and buffzinho < 0):
            falling = 1 - 1 / (2 * self.good_buffer_time / 3) * (buffzinho + 2 * self.good_buffer_time / 3)
            steady  = 1 / (2 * self.good_buffer_time / 3) * (buffzinho + 2 * self.good_buffer_time /3 )
        
        elif (0 <= buffzinho < 4 * self.good_buffer_time):
            steady = 1 - 1 / (4 * self.good_buffer_time) * buffzinho
            rising = 1 / (4 * self.good_buffer_time) * buffzinho
        
        else:
            rising = 1
        
        return (falling, steady, rising)
            
    
    def __association__(self, short, close, long, falling, steady, rising):
        
        # The value of each rule is calculated as the minimum value
        # among the two input functions that comprise it.

        r1 = min (short, falling); r2 = min (close, falling); r3 = min (long, falling); r4 = min (short, steady)
        r5 = min (close, steady); r6 = min (long, steady); r7 = min (short, rising); r8 = min (close, rising)
        r9 = min (long, rising)

        print("r1 ... r9")
        print(r1, r2, r3, r4, r5, r6, r7, r8, r9)

        I  = r9
        SI = sqrt(pow(r6, 2) + pow(r8,2))
        NC = sqrt (pow (r3, 2) + pow (r5, 2) + pow (r7, 2))
        SR = sqrt(pow(r2, 2) + pow(r4,2))
        R  = r1 

        f  = (0.25 * R + 0.5 * SR + 1 * NC + 2 * SI + 4 * I) / (SR + R + NC + SI + I)

        return f

    def __get_quality_index__(self, segment_throughput):
        qi_idx = 0
        i = 0

        while(i < len(self.qi_list)):
            if(self.qi_list[i] < segment_throughput):
                qi_idx = i
            else:
                break

            i += 1

        return qi_idx    

    def handle_segment_size_request(self, msg):
        next_qi_idx = 0

        if(self.segment_idx < 2):
            self.throughput_segments.append(self.qi_list[0])
            next_qi_idx = 0

            if(self.segment_idx >= 1):
                self.last_buffer = self.whiteboard.get_playback_buffer_size()[-1][-1]
        
        else:
            self.request_time = time.perf_counter()

            penult_buffer_time = self.last_buffer
            self.last_buffer = self.whiteboard.get_playback_buffer_size()[-1][-1]
            
            buff_rules = self.__get_buffering_time_degree__(self.last_buffer)
            delta_buff_rules = self.__delta_Bf_degree__(self.last_buffer - penult_buffer_time)

            my_f = self.__association__(*(buff_rules + delta_buff_rules))

            print("\n---------------------------------------------------------------------------------------------")
            print("(short, close, long)")
            print(buff_rules)
            print("(falling, steady, rising)")
            print(delta_buff_rules)
            print(f"Vetor de buffers: {self.throughput_segments}")
            
            # Removing old throughput values according to a buffer time
            if(len(self.throughput_segments) > self.buffer_back_time):
                self.throughput_segments.pop(0)

            average_throughput = mean(self.throughput_segments)

            next_segment_throughput = my_f * average_throughput # (つ◉益◉)つ

            # print(f"A divisao: {average_throughput / next_segment_throughput}")
            # print(f"OLHA SO: {1 / my_f}")

            last_throughput = self.throughput_segments[-1]

            some_seconds = 60 # (∩｀-´)⊃━✿✿✿✿✿✿

            if(next_segment_throughput > last_throughput): # (〜^∇^)〜  (┛◉Д◉)┛彡(|___|
                estimated_buffer = self.last_buffer + (1 / my_f - 1) * some_seconds

                # estimated_buffer = round(estimated_buffer) # (ﾉ◕ヮ◕)ﾉ*:･ﾟ

                print(f"OLHA ISSO AQUI: {estimated_buffer}")
                if(estimated_buffer < self.good_buffer_time):
                    next_segment_throughput = last_throughput
            
            elif(next_segment_throughput < last_throughput):
                estimated_buffer = self.last_buffer + (average_throughput / last_throughput - 1) * some_seconds

                # estimated_buffer = round(estimated_buffer)

                print(f"OLHA ESSE BUFFER: {estimated_buffer}")
                if(estimated_buffer > self.good_buffer_time):
                    next_segment_throughput = last_throughput

            # The quality will fluctuate with this implementation
            next_qi_idx = self.__get_quality_index__(next_segment_throughput)

            print("---------------------------------------------------------------------------------------------")
            print(f"F is {my_f}, Size of TS = {len(self.throughput_segments)}, Average_TP = {average_throughput}")
            print(f"Last buffer: {self.last_buffer}, penult buffer: {penult_buffer_time}, segment_idx = {self.segment_idx}")
            print("---------------------------------------------------------------------------------------------\n")


        self.segment_idx += 1
        # Putting the next segment quality in the msg
        msg.add_quality_id(self.qi_list[next_qi_idx])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        
        t = time.perf_counter() - self.request_time

        self.throughput_segments.append(msg.get_bit_length() / t)
        self.send_up(msg)

    def initialize(self):
        pass

    
    def finalization(self):
        pass
