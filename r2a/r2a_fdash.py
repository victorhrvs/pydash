# -*- coding: utf-8 -*-
"""
@authors: Victor Henrique do Rêgo Vieira de Sousa

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
import matplotlib.pyplot as plt



class R2A_FDash(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []
        self.whiteboard = Whiteboard.get_instance()
        #plt.show()


    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        # time to define the segment quality choose to make the request
        
        msg.add_quality_id(self.qi[5])
        self.fuzzy_factor(3.5, 5.0)

        #gprint(self.whiteboard.get_playback_history())
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass

    def fuzzy_factor(self, bufferT, diffBufferT):
        T = 15
        d = 15 #Delta

        # Cria as variáveis do problema
        bufferTime = ctrl.Antecedent(np.arange(0, 4*T, 0.01), 'bufferTime')
        diffBufferTime = ctrl.Antecedent(np.arange((-2)*T, (4*T)+10, 0.01), 'diffBufferTime')
        bitratefactor = ctrl.Consequent(np.arange(0, 2.5, 0.01), 'bitratefactor')



        # Cria automaticamente o mapeamento entre valores nítidos e difusos 
        # usando uma função de pertinência padrão (triângulo)
        bufferTime['short'] = fuzz.trapmf(bufferTime.universe, [0, 0, (2*T)/3, T])
        bufferTime['close'] = fuzz.trimf(bufferTime.universe, [(2*T)/3, T, 4*T])
        bufferTime['long'] = fuzz.trapmf(bufferTime.universe, [T, 4*T, 10*T, 10*T])


        # Cria as funções de pertinência usando tipos variados
        diffBufferTime['falling'] = fuzz.trapmf(diffBufferTime.universe, [(-10)*T, (-10)*T, ((-2)*T)/3, 0])
        diffBufferTime['steady'] = fuzz.trimf(diffBufferTime.universe, [((-2)*T)/3, 0, 4*T])
        diffBufferTime['rising'] = fuzz.trapmf(diffBufferTime.universe, [0, 4*T, 10*T, 10*T])

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

        return bitratefactor_simulador.output
