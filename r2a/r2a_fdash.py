# -*- coding: utf-8 -*-
"""
Autores: 
        Victor Henrique do Rêgo Vieira de Sousa

@description: PyDash Project

An implementation example of a FDash R2A Algorithm.

the quality list is obtained with the parameter of handle_xml_response() method and the choice
is made inside of handle_segment_size_request(), before sending the message down.
"""
# Se necessário, instale o pacote skfuzzy
#pip install networkx==2.3
#pip install scikit-fuzzy

from base.whiteboard import Whiteboard
from player.parser import *
from r2a.ir2a import IR2A

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

class R2A_FDash(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []
        self.whiteboard = Whiteboard.get_instance()
        self.T = 8  #Valor do artigo T = 35
        self.d = 2  #                d = 60
        self.ultimo = 0.0
        self.penultimo = 0.0
        self.firsTimeOcurrence = True
        self.timeParameter = 0.0

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()
        self.selected_qi = self.qi[0]
        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        # time to define the segment quality choose to make the request
        #msg.add_quality_id(self.qi[5])

        #Algoritmo 1:
        buffer_size = self.get_buffer_size()
        diff_buffer_size = self.get_diff_buffer_size()
        
        # #Algoritmo 2:
        # buffer_size = self.get_segmentTimeOnBuffer()
        # diff_buffer_size = self.get_deltaTi()

        
        factor = self.fuzzy_factor(buffer_size, diff_buffer_size)

        #print(str(buffer_size) + "Buffer_size: " + str(buffer_size) )
        fuzzy_factor = self.selected_qi * factor
        
        print("factor   : "+ str(fuzzy_factor) )
        # Evita que qualidades altas sejam selecionadas repetinamente
        if factor > 1:
            if fuzzy_factor >= self.qi[18]:
                fuzzy_factor = fuzzy_factor * 1.30
            if fuzzy_factor > self.qi[5]:
                fuzzy_factor = fuzzy_factor * 0.6896

        #print("selected qi:", self.selected_qi)
        #print("selected qi x factor:", self.selected_qi * factor)
        print("factor IF: "+ str(fuzzy_factor) )

        for i in self.qi:
            if fuzzy_factor > i:
                self.selected_qi = i
        #print("buffer_size: " + str(buffer_size) + " diff_buffer: " + str(diff_buffer_size) + " fuzzy_factor: " + str(fuzzy_factor) + " selected: " +str(self.selected_qi))

        print(self.selected_qi)
        msg.add_quality_id(self.selected_qi)
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass

    def get_buffer_size(self):
            if len(self.whiteboard.get_playback_buffer_size()) != 0:
                b = self.whiteboard.get_playback_buffer_size()
                return float(b[-1][1])
            return 0.0
    
    def get_diff_buffer_size(self):
        #Retorna o diferencial dos valores de tamanho de buffer 
        timebuffer = self.whiteboard.get_playback_buffer_size() 
        if timebuffer:
            final = 0.0
            final = timebuffer[-1] 
            diff_buffer = 0.0 
            diff_t = 0.0 
            #Lista invertida para acessar os valores mais novos primeiro
            for init in timebuffer[::-1]:
                #delta de tempo = self.d
                if diff_t < self.d:
                    diff_t = final[0] - init[0]
                    diff_buffer = final[1] - init[1]
            return diff_buffer
        return 0.0
    
    def get_segmentTimeOnBuffer(self): 
        #pega a lista com o tamanho do buffer
        bufferSize = self.whiteboard.get_playback_buffer_size()                        

        if len(bufferSize) > 2:
            #se for a primeira vez que um segmento é retirado do buffer
            if self.firsTimeOcurrence == True & bufferSize[-1][1] < bufferSize[-2][1]: 
                
                #tempo de buffer do ultimo segmento 
                self.ultimo = bufferSize[-1][0] - bufferSize[0][0]
                
                #novo parametro de tempo para subtrair do prox segmento retirado do buffer           
                self.timeParameter = bufferSize[-1][0]

                #nao vai mais executar esse if
                self.firsTimeOcurrence = False
 
            elif bufferSize[-1][1] < bufferSize[-2][1]:
                self.penultimo = self.ultimo
                self.ultimo = bufferSize[-1][0] - self.timeParameter
                #novo parametro de tempo
                self.timeParameter = bufferSize[-1][0]
            
        return self.ultimo

    def get_deltaTi(self):
        variacao = self.ultimo - self.penultimo 
        return variacao

    def fuzzy_factor(self, bufferT, diffBufferT):
        T = self.T
        d = self.d #DeltaTime



        # Cria as variáveis do problema
        bufferTime = ctrl.Antecedent(np.arange(0, 4*T, 0.01), 'bufferTime')
        diffBufferTime = ctrl.Antecedent(np.arange((-2)*d, (4*d)+10, 0.005), 'diffBufferTime')
        bitratefactor = ctrl.Consequent(np.arange(0, 2.5, 0.01), 'bitratefactor')



        # Cria automaticamente o mapeamento entre valores nítidos e difusos 
        # usando uma função de pertinência padrão (triângulo)
        bufferTime['short'] = fuzz.trapmf(bufferTime.universe, [0, 0, (2*T)/3, T])
        bufferTime['close'] = fuzz.trimf(bufferTime.universe, [(2*T)/3, T, 4*T])
        bufferTime['long'] = fuzz.trapmf(bufferTime.universe, [T, 4*T, 10*T, 10*T])


        # Cria as funções de pertinência usando tipos variados
        diffBufferTime['falling'] = fuzz.trapmf(diffBufferTime.universe, [-120, -120, ((-2)*d)/3, 0])
        diffBufferTime['steady'] = fuzz.trimf(diffBufferTime.universe, [((-2)*d)/3, 0, 4*d])
        diffBufferTime['rising'] = fuzz.trapmf(diffBufferTime.universe, [0, 4*d, 10*d, 10*d])

        N2 = 0.25
        N1 = 0.5
        Z = 1
        P1 = 1.5
        P2 = 2

        bitratefactor['reduce'] = fuzz.trapmf(bitratefactor.universe, [0, 0, N2, N1])
        bitratefactor['small reduce'] = fuzz.trimf(bitratefactor.universe, [N2, N1, Z])
        bitratefactor['no change'] = fuzz.trimf(bitratefactor.universe, [N1, Z, P1])
        bitratefactor['small increase'] = fuzz.trimf(bitratefactor.universe, [Z, P1, P2])
        bitratefactor['increase'] = fuzz.trapmf(bitratefactor.universe, [P1, P2,2.5, 2.5])


        rule1 = ctrl.Rule(bufferTime['short'] & diffBufferTime['falling'], bitratefactor['reduce'])
        rule2 = ctrl.Rule(bufferTime['close'] & diffBufferTime['falling'], bitratefactor['small reduce'])
        rule3 = ctrl.Rule(bufferTime['long'] & diffBufferTime['falling'], bitratefactor['no change'])
        rule4 = ctrl.Rule(bufferTime['short'] & diffBufferTime['steady'], bitratefactor['small reduce'])
        rule5 = ctrl.Rule(bufferTime['close'] & diffBufferTime['steady'], bitratefactor['no change'])
        rule6 = ctrl.Rule(bufferTime['long'] & diffBufferTime['steady'], bitratefactor['small increase'])
        rule7 = ctrl.Rule(bufferTime['short'] & diffBufferTime['rising'], bitratefactor['no change'])
        rule8 = ctrl.Rule(bufferTime['close'] & diffBufferTime['rising'], bitratefactor['small increase'])
        rule9 = ctrl.Rule(bufferTime['long'] & diffBufferTime['rising'], bitratefactor['increase'])

        bitratefactor_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9])
        bitratefactor_simulador = ctrl.ControlSystemSimulation(bitratefactor_ctrl)

        # Entrando com alguns valores para qualidade da comida e do serviço
        # Eixo X do gráfico
        bitratefactor_simulador.input['bufferTime'] = bufferT 
        bitratefactor_simulador.input['diffBufferTime'] = diffBufferT

        # Computando o resultado
        bitratefactor_simulador.compute()

        print("BitrateAtual * ", bitratefactor_simulador.output['bitratefactor'])
        """
        #Gera 3 graficos quando buffir_size = 50
        import matplotlib.pyplot as plt
        if bufferT == 50:
            bufferTime.view(sim=bitratefactor_simulador)
            diffBufferTime.view(sim=bitratefactor_simulador)
            bitratefactor.view(sim=bitratefactor_simulador)
        
            plt.show()
        """
        return bitratefactor_simulador.output['bitratefactor']
