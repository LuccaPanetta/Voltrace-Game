# ===================================================================
# CEREBRO IA (DEEP Q-NETWORK)
# ===================================================================

import random
import numpy as np
from collections import deque
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


# Red neuronal de 9 entradas → 5 acciones posibles.
class VoltraceCerebro(nn.Module):
    def __init__(self, input_size=9, hidden_size=64, output_size=5):
        super(VoltraceCerebro, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)


class VoltraceAgent:
    def __init__(self, input_size=9, output_size=5):
        self.cerebro = VoltraceCerebro(input_size, output_size)
        self.optimizer = optim.Adam(self.cerebro.parameters(), lr=0.001)
        self.memory = deque(maxlen=2000)

        self.gamma = 0.95  # Peso de recompensas futuras
        self.epsilon = 1.0  # Exploración inicial (100% aleatorio)
        self.epsilon_min = 0.05  # Piso mínimo de exploración
        self.epsilon_decay = 0.995  # Velocidad de decay
        self.action_size = output_size

    # Guarda una transición (s, a, r, s', done) en la memoria de replay.
    def recordar_jugada(self, estado, accion, recompensa, siguiente_estado, finalizado):
        self.memory.append((estado, accion, recompensa, siguiente_estado, finalizado))

    # Explora al azar o explota la red neuronal
    def tomar_decision(self, estado):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)

        estado_tensor = torch.FloatTensor(estado)
        with torch.no_grad():
            valores_q = self.cerebro(estado_tensor)
        return torch.argmax(valores_q).item()

    # Aplica la ecuación de Bellman sobre un minibatch aleatorio de la memoria.
    def entrenar_memoria(self, batch_size=32):
        pass

    # Aplica la ecuación de Bellman sobre un minibatch aleatorio de la memoria.
    def entrenar_memoria(self, batch_size=32):
        if len(self.memory) < batch_size:
            return

        minibatch = random.sample(self.memory, batch_size)

        # Desempaquetar transiciones y convertir a tensores
        estados = torch.FloatTensor(np.array([t[0] for t in minibatch]))
        acciones = torch.LongTensor([t[1] for t in minibatch]).unsqueeze(1)
        recompensas = torch.FloatTensor([t[2] for t in minibatch])
        siguientes_estados = torch.FloatTensor(np.array([t[3] for t in minibatch]))
        finalizados = torch.FloatTensor([t[4] for t in minibatch])

        # Q-values actuales de las acciones tomadas
        q_actuales = self.cerebro(estados).gather(1, acciones).squeeze(1)

        # Q-values máximos futuros (Ecuación de Bellman)
        with torch.no_grad():
            q_siguientes = self.cerebro(siguientes_estados).max(1)[0]

        q_objetivos = recompensas + (self.gamma * q_siguientes * (1 - finalizados))

        # Calcular pérdida (MSE) y optimizar pesos
        criterio = nn.MSELoss()
        loss = criterio(q_actuales, q_objetivos)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # Decay de exploración (Epsilon)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
