# -*- coding: utf-8 -*-
"""
Modulo que implementa o algoritmo de taxa de selecao de bits dentro da pilha 
que define o cliente Dash
"""

from r2a.ir2a import IR2A
from player.parser import *
from math import pow, sqrt
import time
from statistics import mean

class R2A_FDash(IR2A):
    """ Classe que implementa o algoritmo de adaptacao de bitrate.
    
    Esta classe implementa o algoritmo de adapatacao de taxa de bits FDash. Dentro da pilha do 
    cliente DASH, este modulo tem por funcao determinar a melhor qualidade possivel para o download 
    de segmentos de video requisitados, a depender da qualidade da rede. Com isto, a classe busca 
    baixar os segmentos de forma que a qualidade fique estavel.

    @warn Prefira usar esta classe com python 3.5 ou uma versao mais recente

    """

    def __init__(self, id):

        IR2A.__init__(self, id)
        self.last_buffer_time    = 0
        self.penult_buffer_time  = 0
        self.good_buffer_time    = 22      # Represents the buffer in seconds
        self.throughput_segments = []
        self.qi_list             = []      # The list of qualitys
        self.last_buffer         = 0
        self.buffer_back_time    = self.good_buffer_time / 2
        self.request_time = 0
        self.segment_idx = 0

        # If turned on, print some function's values on the terminal
        self.debug_mode          = False   

    def handle_xml_request(self, msg):
        """
        Trata de requisicoes xml do player.

        @brief Trata das requisicoes do player, passando a requisicao para a proxima camada.

        @param msg: mensagem do tipo base.Message, com a requisicao inicial dos videos.
        """
        self.request_time = time.perf_counter()

        self.send_down(msg)

    
    def handle_xml_response(self, msg):
        """
        Responde a uma requisicoes xml do player.

        @brief Encaminha a requisicao vinda do modulo ConnectionHandler para o Player.
    
        @param msg: a mensagem do tipo base.Message, com todos os dados requisitados pelo player.
        """
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi_list = parsed_mpd.get_qi()

        self.send_up(msg)

    def __get_buffering_time_degree__(self, last_bt):
        """
        Executa o passo de difusao no ultimo tempo de buffer recebido.
        
        @description Dado o ultimo tempo de buffer recebido, calcula a difusao do tempo de buffer do 
        ultimo segmento recebido, e o traduz em graus de difusao para uso na execucao do programa. Esta 
        funcao considera o tempo de buffer ideal definido no metodo __init__ para calcular o grau de saida.

        @param last_bt: um inteiro indicando o tempo em que o ultimo segmento no buffer deve tocar no player
        (last_bt = last buffer time).

        @return Retorna uma tupla de 3 elementos, com o resultado da difusao da saida.
        """
        short = close = long = 0
        
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
    

    def __delta_Bf_degree__(self, diff_bt):
        """
        Dado a diferenca de tempo recebida, converte-a em graus de difusao.

        @description executa a difusao na diferenca de tempo entre o ultimo e o penultimo tempo de buffers. 
        Considera o tempo de buffer ideal definido no metodo __init__. Em sua execucao, verifica se a diferenca 
        em graus esta caindo, constante ou subindo.

        @param diff_bt: valor de ponto flutuante que contem a diferenca de tempo entre o ultimo e o penultimo 
        tempo de buffer.

        @return Retorna uma tupla de 3 elementos, com os valores difusos calculados.
        """
        falling = rising = steady = 0            

        if (diff_bt <= (-2 * self.good_buffer_time) / 3):
            falling = 1
        
        elif (diff_bt > (-2 * self.good_buffer_time)/3 and diff_bt < 0):
            falling = 1 - 1 / (2 * self.good_buffer_time / 3) * (diff_bt + 2 * self.good_buffer_time / 3)
            steady  = 1 / (2 * self.good_buffer_time / 3) * (diff_bt + 2 * self.good_buffer_time /3 )
        
        elif (0 <= diff_bt < 4 * self.good_buffer_time):
            steady = 1 - 1 / (4 * self.good_buffer_time) * diff_bt
            rising = 1 / (4 * self.good_buffer_time) * diff_bt
        
        else:
            rising = 1
        
        return (falling, steady, rising)
            
    
    def __fuzzy_association__(self, short, close, long, falling, steady, rising):
        """
        Relaciona as entradas difusas a uma saida final.

        @description Executa, de acordo com os valores de entrada, e gera um valor de saida 
        resultante. O metodo recebe os valores difusos calculados em funcoes anteriores, executa 
        o calculo para converter estas entradas em valores usaveis na saida e a retorna. As variaveis 
        short, close e long sao os calculados na funcao __get_buffering_time_degree__ e falling, steady e 
        rising as variaveis calculadas no metodo __delta_Bf_degree__.

        @param short, close, long: int
        @param falling, steady, rising: int
        """
        # The value of each rule is calculated as the minimum value
        # among the two input functions that comprise it.

        r1 = min (short, falling); r2 = min (close, falling); r3 = min (long, falling); r4 = min (short, steady)
        r5 = min (close, steady); r6 = min (long, steady); r7 = min (short, rising); r8 = min (close, rising)
        r9 = min (long, rising)

        if(self.debug_mode):
            print("r1 ... r9")
            print(r1, r2, r3, r4, r5, r6, r7, r8, r9)


        I  = r9
        SI = sqrt(pow(r6, 2) + pow(r8,2))
        NC = sqrt (pow (r3, 2) + pow (r5, 2) + pow (r7, 2))
        SR = sqrt(pow(r2, 2) + pow(r4,2))
        R  = r1 

        # The "defuzzification" step. It take the calculated values and get an aproprieted output, 
        # the proportion of the next segment throughput
        f  = (0.25 * R + 0.5 * SR + 1 * NC + 2 * SI + 4 * I) / (SR + R + NC + SI + I)

        return f

    def __get_quality_index__(self, segment_throughput):
        """
        Recebe um throughput e calcula o indice correto na lista de qualidades.

        @description Verifica, na lista de qualidades do video, o indice da qualidade que corresponde 
        a segment_throughput. Retorna o indice da maior qualidade possivel, necessariamente menor que 
        segment_throughput.

        @param segment_thoughput: A vazao do segmento de referencia

        @return Um indice no intervalo [0, 1, ..., tamanho(qi_list)], (qi_list eh o vetor de todas as qualidades 
        possiveis) que indica a maior qualidade possivel verificada.
        """
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
        """
        Recebe uma requisicao de segmento do modulo Player e a encaminha para o modulo de conexao, escolhendo a qualidade apropriada.

        @description: esta funcao recebe uma mensagem da classe base.SSMessage e configura a qualidade 
        na qual o proximo segmento sera baixado. Para tal, tenta prever a qualidade do proximo segmento 
        atraves do processo de difusao. Primeiro, recebe os valores dos tempos de buffers do player, 
        e chama as funcoes necessarias para executar a difusao. Em seguida, recebe o valor resultante 
        deste processo chamando a funcao __fuzzy_association__. Este valor eh uma medida de proporcao da 
        vazao que o proximo segmento de video tera. Com isto, calcula a melhor qualidade usando-se da lista 
        de qualidades possiveis. E necessario ressaltar que esta funcao tenta manter uma taxa de download 
        estavel ao receber requisicoes.

        @param msg: objeto do tipo base.SSMessage que contem a requisicao de segmentos de video vinda 
        do Player. 
        """
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

            my_f = self.__fuzzy_association__(*(buff_rules + delta_buff_rules))

            if(self.debug_mode):
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

            next_segment_throughput = my_f * average_throughput

            last_throughput = self.throughput_segments[-1]

            some_seconds = 60

            if(next_segment_throughput > last_throughput):
                estimated_buffer = self.last_buffer + (1 / my_f - 1) * some_seconds

                # estimated_buffer = round(estimated_buffer)

                if(self.debug_mode):
                    print(f"OLHA ISSO AQUI: {estimated_buffer}")

                if(estimated_buffer < self.good_buffer_time):
                    next_segment_throughput = last_throughput
            
            elif(next_segment_throughput < last_throughput):
                estimated_buffer = self.last_buffer + (average_throughput / last_throughput - 1) * some_seconds

                # estimated_buffer = round(estimated_buffer)

                if(self.debug_mode):
                    print(f"OLHA ESSE BUFFER: {estimated_buffer}")

                if(estimated_buffer > self.good_buffer_time):
                    next_segment_throughput = last_throughput

            # The quality will fluctuate with this implementation
            next_qi_idx = self.__get_quality_index__(next_segment_throughput)


            if(self.debug_mode):
                print("---------------------------------------------------------------------------------------------")
                print(f"F is {my_f}, Size of TS = {len(self.throughput_segments)}, Average_TP = {average_throughput}")
                print(f"Last buffer: {self.last_buffer}, penult buffer: {penult_buffer_time}, segment_idx = {self.segment_idx}")
                print("---------------------------------------------------------------------------------------------\n")


        self.segment_idx += 1
        # Putting the next segment quality in the msg
        msg.add_quality_id(self.qi_list[next_qi_idx])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        """
        Recebe uma mensagem do modulo de conexao e encaminha para o modulo de Player.

        @description: ao receber o objeto do tipo base.SSMessage vinda do modulo de conexao, 
        encaminha a resposta para o modulo de player. Alem disso, calcula a vazao real de 
        download do ultimo segmento baixado.

        @param msg: objeto do tipo base.SSMessage vindo do modulo de conexao. Contem o segmento 
        de video requisitado.
        """
        
        t = time.perf_counter() - self.request_time

        self.throughput_segments.append(msg.get_bit_length() / t)
        self.send_up(msg)

    def initialize(self):

        print("\n---------------------------------------------------------------------------------------------")
        out_msg = "MODO DE DEPURACAO: "
        if(self.debug_mode):
            print(out_msg + "Ligado")

        else:
            print(out_msg + "Desligado")
        print("---------------------------------------------------------------------------------------------\n")

    
    def finalization(self):
        pass
