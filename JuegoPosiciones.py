# Ejercicio juego posiciones (AS)
from random import randint

class jugador():
	# data as integer
	# nextnode as integer
	def __init__ (self, nombre):
		self.__nombre = nombre
		self.__posicion= 0
		self.__puntaje= 500
		self.__ok = True
		
	def getNombre (self):
		return self.__nombre
		
	def getPosicion (self):
		return self.__posicion

	def getPuntaje (self):
		return self.__puntaje

	def getOk (self):
		return self.__ok
		
	def avanzar (self, posiciones):
		self.__posicion = self.__posicion + posiciones
		
	def procesarEnergia (self, energia):
		self.__puntaje = self.__puntaje + energia
		if self.__puntaje < 0:
			self.__ok = False


# Variables globales 
arraySorpresa=[]  # nombre, posición, valor
arrayEnergia=[]   # todas las "sorpresas" leídas del archivo
arrayJugadores=[] # contiene objetos de clase Jugador
fin=False

def ProcesarArchivoEnergia():
	try:
		energia_file= open("packenergia.txt")
	except:
		print ("File not found, no energy processed")
	energia_linea = (energia_file.readline())
	while len(energia_linea) > 0:
		Sorpresa=[]
		a,b,c = energia_linea.split(",", 2)
		nombre=a
		posicion=int(b)
		valor=int(c.strip())
		Sorpresa.append(nombre)
		Sorpresa.append(posicion)
		Sorpresa.append(valor)
		arrayEnergia.append(Sorpresa)
		energia_linea = (energia_file.readline())
	energia_file.close()

def SetPlayers():
	print("La cantidad de jugadores es de 2 a 5.  Ingresar los nombre e ingresar N como nombre si no hay más jugadores")
	playername=input("ingresar nombre jugador")
	arrayJugadores.append(jugador(playername))
	playername=input("ingresar nombre jugador")
	arrayJugadores.append(jugador(playername))
	opcion=input("Más jugadores? S para agregar más")
	while opcion.upper() =="S" and len(arrayJugadores)<5:
		playername=input("ingresar nombre jugador")
		arrayJugadores.append(jugador(playername))
		opcion=input("Más jugadores? S para agregar más")
	print("Listo Jugadores")

def ControlFinJuego():
	fin=False
	# Control de jugadores activos
	cantidad_fuera = 0
	for i in range (len(arrayJugadores)):
		if arrayJugadores[i].getOk() == False:
			cantidad_fuera +=1
	if (len(arrayJugadores) - cantidad_fuera) < 2:
		fin=True
	# Control de que algún jugador haya llegado al final
	for i in range (len(arrayJugadores)):
		if arrayJugadores[i].getPosicion() >= 50:
			fin=True
	return fin

def PuntajeFinal():
	# busco mayor posicion
	max_posicion=0
	for t in range (len(arrayJugadores)):
		if arrayJugadores[t].getPosicion() > max_posicion:
			max_posicion = arrayJugadores[t].getPosicion()
	print("El que llegó mas jlejos está en " + str(max_posicion))
	if max_posicion >=50:
		for i in range (len(arrayJugadores)):
			if arrayJugadores[i].getPosicion() != max_posicion:
				if arrayJugadores[i].getOk:
					arrayJugadores[i].procesarEnergia(-(max_posicion - arrayJugadores[i].getPosicion() ) *5)
	else:
		for i in range (len(arrayJugadores)):
			if arrayJugadores[i].getPosicion() != max_posicion:
				if arrayJugadores[i].getOk:
					arrayJugadores[i].procesarEnergia(-(max_posicion - arrayJugadores[i].getPosicion() ) *3)
			
def DeterminaGanador():
	# busco mayor posicion
	array_winners=[]
	array_max_position=[]
	max_puntaje=0
	cant_ganadores=0
	for i in range (len(arrayJugadores)):
		if arrayJugadores[i].getPuntaje() > max_puntaje:
			max_puntaje = arrayJugadores[i].getPuntaje()
	for i in range (len(arrayJugadores)):
		if arrayJugadores[i].getPuntaje() == max_puntaje:
			array_winners.append(i)
	if len(array_winners) == 1:
		print("the winner is " + arrayJugadores[array_winners[0]].getNombre() )
	else:
		print("empate x puntos")
		max_posicion=0
		cant_max_pos = 0
		for j in range (len(array_winners)):
			if arrayJugadores[array_winners[j]] > max_posicion:
				max_posicion = arrayJugadores[array_winners[j]]
				cant_max_pos +=1
				array_max_position.append(array_winners[j])
			print("the winner is " + arrayJugadores[array_max_position[0]].getNombre() )
			if cant_max_pos > 1:
				print("con igual cnatidad putnos y posicion")
			
			
		



# Programa principal
ProcesarArchivoEnergia()
SetPlayers()
while fin == False:
	for i in range (len(arrayJugadores)):
		if arrayJugadores[i].getOk():
			playername = arrayJugadores[i].getNombre()
			print("Turno jugador " + playername)
			input("Presione Enter para continuar")
			avanzar=randint(1,5)
			print("Hay que avanzar " + str(avanzar) + " posiciones")
			arrayJugadores[i].avanzar(avanzar)
			dondeestoy=arrayJugadores[i].getPosicion()
			print("posición " + str(dondeestoy))
			energiaencontrada = 0
			# Verifico si hay energía en la posición que caí
			for j in range (len(arrayEnergia)):
				if dondeestoy == arrayEnergia[j][1]:
					energiaencontrada = arrayEnergia[j][2]
					print("en la posiión hay energía: " + str(energiaencontrada))
					arrayEnergia[j][2] = arrayEnergia[j][2] // 2
					break
			arrayJugadores[i].procesarEnergia(energiaencontrada)
			# Controlo si hay otro jugador en la posición donde caí
			for k in range (len(arrayJugadores)):
				hayotro=0
				if dondeestoy == arrayJugadores[k].getPosicion() and k!=i:
					hayotro=1
					arrayJugadores[k].procesarEnergia(-100)
					print("Colisión!! pérdida de energía!!!")
				if hayotro==1:
					arrayJugadores[i].procesarEnergia(-100)   # lo hago así x las dudas colisión triple! 
		else:
			continue
	fin=ControlFinJuego()
	seguir=input("Seguir? X mayúscula para para anticipadamente")
	if seguir == 'X':
		fin=True
PuntajeFinal()
DeterminaGanador()



print("Status final")
print("Jugador".center(20) + "Posicion".center(10) + "Puntaje".center(10) + "Ok".center(10) )
for i in range (len(arrayJugadores)):
	print(arrayJugadores[i].getNombre().center(20) + str(arrayJugadores[i].getPosicion()).center(10) + str(arrayJugadores[i].getPuntaje()).center(10) + str(arrayJugadores[i].getOk()).center(10) )
