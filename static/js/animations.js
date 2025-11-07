/* ===================================================================
   SISTEMA DE ANIMACIONES DEL CLIENTE - VOLTRACE (animations.js)
   ===================================================================
   
   Este archivo define la clase 'AnimationSystem' (expuesta como
   window.GameAnimations) que maneja todos los efectos visuales
   del cliente.
   
   Responsabilidades:
   - animatePlayerMove: Movimiento de fichas entre casillas (obsoleto
     si se usa CSS, pero podría ser para efectos complejos).
   - shakeBoard: Efecto de sacudida para trampas/colisiones.
   - animateAbilityUse / animateEnergyChange: Efectos visuales para
     habilidades y cambios de energía (usando clases de animations.css).
   - celebrateVictory / createConfetti: Efectos de victoria.
   - animateAchievement: Notificación de logro desbloqueado.
   - transitionScreen: Transiciones suaves entre pantallas.
   - animateDiceRoll: Animación del dado.
   
   =================================================================== */

export class AnimationSystem {
  /**
   * Constructor del sistema de animaciones
   * Inicializa el estado y configuración del sistema
   */
  constructor() {
    // Cargar preferencia de animaciones desde localStorage (por defecto: activado)
    this.isEnabled = localStorage.getItem('animations_enabled') !== 'false';
    
    // Array para trackear partículas activas (para cleanup)
    this.particles = [];
    
    // Flag para controlar el efecto confetti
    this.confettiActive = false;
  }

  /**
   * Alternar el estado de las animaciones (on/off)
   * Guarda la preferencia en localStorage para persistencia
   */
  toggleAnimations() {
    this.isEnabled = !this.isEnabled;
    localStorage.setItem('animations_enabled', this.isEnabled.toString());
  }

  /**
   * Anima el movimiento de una ficha de jugador de una casilla a otra
   * Crea una ficha temporal que se mueve suavemente por el tablero
   * 
   * @param {number} fromPosition - Posición inicial (1-75)
   * @param {number} toPosition - Posición final (1-75)
   * @param {string} playerName - Nombre del jugador (para mostrar inicial)
   * @param {function} callback - Función a ejecutar al completar animación
   */
  animatePlayerMove(fromPosition, toPosition, playerName, callback = null) {
    if (!this.isEnabled) {
      if (callback) callback();
      return;
    }

    const fromCell = document.querySelector(`[data-position="${fromPosition}"]`);
    const toCell = document.querySelector(`[data-position="${toPosition}"]`);
    
    if (!fromCell || !toCell) {
      if (callback) callback();
      return;
    }

    const pieceToMove = fromCell.querySelector(`.ficha-jugador[data-username="${playerName}"]`);

    if (!pieceToMove) {
        // No se encontró la ficha (probablemente ya se movió por updateTablero), no animar.
        if (callback) callback();
        return;
    }

    // Clonar la ficha
    const animPiece = pieceToMove.cloneNode(true);

    // Aplicar estilos de animación (sin borrar el color de fondo)
    animPiece.style.position = 'absolute';
    animPiece.style.zIndex = '1000';
    animPiece.style.pointerEvents = 'none';
    animPiece.style.transition = 'all 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)';

    const fromRect = fromCell.getBoundingClientRect();
    const toRect = toCell.getBoundingClientRect();
    
    // Setear posición inicial
    animPiece.style.left = `${fromRect.left + (fromRect.width / 2) - (animPiece.offsetWidth / 2)}px`;
    animPiece.style.top = `${fromRect.top + (fromRect.height / 2) - (animPiece.offsetHeight / 2)}px`;
    
    document.body.appendChild(animPiece);

    // Animar a la posición final
    requestAnimationFrame(() => {
        animPiece.style.left = `${toRect.left + (toRect.width / 2) - (animPiece.offsetWidth / 2)}px`;
        animPiece.style.top = `${toRect.top + (toRect.height / 2) - (animPiece.offsetHeight / 2)}px`;
    });
    
    // Limpiar el clon después de la animación
    setTimeout(() => {
      animPiece.remove(); 
      if (callback) callback();
    }, 500); // 0.5s
  }

  // Efecto shake para cuando caes en trampa
  shakeBoard(intensity = 'normal') {
    if (!this.isEnabled) return;

    const tablero = document.getElementById('tablero');
    if (!tablero) return;

    const shakeClass = intensity === 'intense' ? 'animate-intense-shake' : 'animate-shake';
    tablero.classList.add(shakeClass);
    
    setTimeout(() => {
      tablero.classList.remove(shakeClass);
    }, 600);
  }

  isCosmeticUnlocked(kitId) {
        const unlockedList = window.VOLTRACE_COSMETICS || []; 
        return unlockedList.includes(kitId);
    }

  // Efecto de habilidad usada
  animateAbilityUse(abilityType, sourceElement) {
    if (!this.isEnabled || !sourceElement) return;

    sourceElement.classList.add('animate-ability-cast');
    
    // Crear partículas según el tipo de habilidad
    this.createParticles(sourceElement, abilityType, 8);

    setTimeout(() => {
      sourceElement.classList.remove('animate-ability-cast');
    }, 800);
  }

  // Efecto de energía ganada/perdida
  animateEnergyChange(element, type = 'gain') {
    if (!this.isEnabled || !element) return;

    const animationClass = type === 'gain' ? 'animate-energy-pulse' : 'animate-damage-flash';
    element.classList.add(animationClass);
    
    setTimeout(() => {
      element.classList.remove(animationClass);
    }, 1800);
  }

  // Celebración de victoria
  celebrateVictory(winnerName) {
    if (!this.isEnabled) return;

    // Animar tablero
    const tablero = document.getElementById('tablero');
    if (tablero) {
      tablero.classList.add('animate-victory');
      setTimeout(() => {
        tablero.classList.remove('animate-victory');
      }, 3600);
    }

    // Crear confetti
    this.createConfetti();

    // Mostrar mensaje de victoria con animación
    this.showVictoryMessage(winnerName);
  }

  // Crear efecto confetti
  createConfetti() {
    if (!this.isEnabled) return;

    this.confettiActive = true;
    const colors = ['#6366f1', '#fbbf24', '#22c55e', '#ec4899', '#8b5cf6'];
    
    for (let i = 0; i < 50; i++) {
      setTimeout(() => {
        if (!this.confettiActive) return;
        
        const piece = document.createElement('div');
        piece.className = 'confetti-piece';
        piece.style.cssText = `
          position: fixed;
          left: ${Math.random() * window.innerWidth}px;
          top: -10px;
          background: ${colors[Math.floor(Math.random() * colors.length)]};
          z-index: 1000;
          pointer-events: none;
        `;
        
        document.body.appendChild(piece);
        
        setTimeout(() => piece.remove(), 3000);
      }, i * 100);
    }

    // Detener confetti después de 5 segundos
    setTimeout(() => {
      this.confettiActive = false;
    }, 5000);
  }

  // Mostrar mensaje de victoria
  showVictoryMessage(winnerName) {
    const message = document.createElement('div');
    message.className = 'victory-message';
    message.innerHTML = `
      <h2>🏆 ¡${winnerName} Gana!</h2>
      <p>¡Felicitaciones por la victoria!</p>
    `;
    message.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      color: white;
      padding: 30px 40px;
      border-radius: 15px;
      text-align: center;
      z-index: 1001;
      font-family: inherit;
      animation: bounce-in 0.8s ease-out;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    `;

    message.querySelector('h2').style.cssText = 'margin: 0 0 10px 0; font-size: 24px;';
    message.querySelector('p').style.cssText = 'margin: 0; opacity: 0.9;';

    document.body.appendChild(message);

    setTimeout(() => {
      message.style.animation = 'fade-out 0.5s ease-in forwards';
      setTimeout(() => message.remove(), 500);
    }, 3000);
  }

  // Crear partículas para efectos
  createParticles(sourceElement, type = 'magic', count = 5) {
    if (!this.isEnabled || !sourceElement) return;

    const rect = sourceElement.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    for (let i = 0; i < count; i++) {
      setTimeout(() => {
        const particle = document.createElement('div');
        particle.className = `particle ${type}`;
        
        const angle = (360 / count) * i;
        const distance = 30 + Math.random() * 20;
        const x = centerX + Math.cos(angle * Math.PI / 180) * distance;
        const y = centerY + Math.sin(angle * Math.PI / 180) * distance;
        
        particle.style.cssText = `
          position: fixed;
          left: ${centerX}px;
          top: ${centerY}px;
          z-index: 999;
          pointer-events: none;
        `;
        
        document.body.appendChild(particle);
        
        // Animar partícula
        requestAnimationFrame(() => {
          particle.style.transition = 'all 1s ease-out';
          particle.style.left = `${x}px`;
          particle.style.top = `${y}px`;
          particle.style.opacity = '0';
        });
        
        setTimeout(() => particle.remove(), 1000);
      }, i * 50);
    }
  }

  // Animar logro desbloqueado
  animateAchievement(achievementElement) {
    if (!this.isEnabled || !achievementElement) return;

    achievementElement.classList.add('animate-achievement-enter');
    
    setTimeout(() => {
      achievementElement.classList.remove('animate-achievement-enter');
    }, 2600);
  }

  // Transición suave entre pantallas
  transitionScreen(fromScreen, toScreen, callback = null) {
    if (!this.isEnabled) {
      fromScreen.classList.remove('active');
      toScreen.classList.add('active');
      if (callback) callback();
      return;
    }

    fromScreen.classList.add('animate-fade-out');
    
    setTimeout(() => {
      fromScreen.classList.remove('active', 'animate-fade-out');
      toScreen.classList.add('active');
      
      if (callback) callback();
    }, 400);
  }

  // Efecto hover para casillas especiales
  highlightSpecialTile(tileElement) {
    if (!this.isEnabled || !tileElement) return;
    tileElement.classList.add('special-tile');
  }

  // Animar dado girando
  animateDiceRoll(diceElement, finalValue, callback = null) {
    if (!this.isEnabled || !diceElement) {
      if (callback) callback();
      return;
    }

    let rollCount = 0;
    const maxRolls = 10;
    
    const rollInterval = setInterval(() => {
      const randomValue = Math.floor(Math.random() * 6) + 1;
      diceElement.textContent = `🎲 ${randomValue}`;
      diceElement.style.transform = `rotate(${rollCount * 36}deg)`;
      
      rollCount++;
      
      if (rollCount >= maxRolls) {
        clearInterval(rollInterval);
        diceElement.textContent = `🎲 ${finalValue}`;
        diceElement.style.transform = 'rotate(0deg)';
        diceElement.classList.add('animate-bounce-in');
        
        setTimeout(() => {
          diceElement.classList.remove('animate-bounce-in');
          if (callback) callback();
        }, 500);
      }
    }, 100);
  }

  /**
   * Reproduce la animación cosmética "Sabotaje Sónico" (Maestría Nv. 10 Táctico).
   * @param {string} playerName - El nombre del jugador que usa la habilidad.
   */
  playSabotageCosmetic(playerName) {
    if (!this.isEnabled) return;

    // Encontrar la ficha (pieza) del jugador en el tablero
    const playerPiece = document.querySelector(`.ficha-jugador[data-username="${playerName}"]`);
    if (!playerPiece) {
        console.warn(`[AnimSystem] No se encontró la ficha para ${playerName} (Sabotaje Sónico).`);
        return;
    }

    // Crear el elemento de la animación
    const animElement = document.createElement('div');
    animElement.className = 'cosmetic-animation sabotage-sonic';
    
    // Posicionar el elemento (centrado en la ficha)
    // Usamos getBoundingClientRect() para obtener la posición en la pantalla
    const pieceRect = playerPiece.getBoundingClientRect();
    const pieceSize = playerPiece.offsetWidth; // ej: 18px
    const animSize = 60; // Definido en el CSS
    
    animElement.style.left = `${pieceRect.left + (pieceSize / 2) - (animSize / 2)}px`;
    animElement.style.top = `${pieceRect.top + (pieceSize / 2) - (animSize / 2)}px`;

    document.body.appendChild(animElement); // Añadir al body

    // Limpiar después de que termine la animación (0.7s)
    setTimeout(() => {
        animElement.remove();
    }, 700);
  }

  /**
   * Reproduce la animación cosmética "Bomba de Pulso" (Maestría Nv. 10 Ingeniero).
   * @param {string} playerName - El nombre del jugador que usa la habilidad.
   */
  playPulseBombCosmetic(playerName) {
    if (!this.isEnabled) return;

    const playerPiece = document.querySelector(`.ficha-jugador[data-username="${playerName}"]`);
    if (!playerPiece) {
        console.warn(`[AnimSystem] No se encontró la ficha para ${playerName} (Bomba de Pulso).`);
        return;
    }

    // Crear el elemento de la animación
    const animElement = document.createElement('div');
    animElement.className = 'cosmetic-animation pulse-bomb'; 
    
    // Posicionar el elemento (centrado en la ficha)
    const pieceRect = playerPiece.getBoundingClientRect();
    const pieceSize = playerPiece.offsetWidth;
    const animSize = 100; 
    
    animElement.style.left = `${pieceRect.left + (pieceSize / 2) - (animSize / 2)}px`;
    animElement.style.top = `${pieceRect.top + (pieceSize / 2) - (animSize / 2)}px`;

    document.body.appendChild(animElement); // Añadir al body

    // Limpiar después de 0.5s (la duración de la animación)
    setTimeout(() => {
        animElement.remove();
    }, 500);
  }

  /**
   * Reproduce la animación cosmética "Fase Sombría" (Maestría Nv. 10 Espectro).
   * @param {string} playerName - El nombre del jugador que usa la habilidad.
   */
  playPhaseShiftCosmetic(playerName) {
    if (!this.isEnabled) return;

    const playerPiece = document.querySelector(`.ficha-jugador[data-username="${playerName}"]`);
    if (!playerPiece) {
        console.warn(`[AnimSystem] No se encontró la ficha para ${playerName} (Fase Sombría).`);
        return;
    }

    // Crear el elemento de la animación
    const animElement = document.createElement('div');
    animElement.className = 'cosmetic-animation phase-shift'; // <-- Cambio de clase
    
    // Posicionar el elemento (centrado en la ficha)
    const pieceRect = playerPiece.getBoundingClientRect();
    const pieceSize = playerPiece.offsetWidth;
    const animSize = 40; // Definido en el CSS
    
    animElement.style.left = `${pieceRect.left + (pieceSize / 2) - (animSize / 2)}px`;
    animElement.style.top = `${pieceRect.top + (pieceSize / 2) - (animSize / 2)}px`;

    document.body.appendChild(animElement); // Añadir al body

    // Limpiar después de 1.2s (la duración de la animación)
    setTimeout(() => {
        animElement.remove();
    }, 1200);
  }

  /**
   * Reproduce la animación cosmética "Escudo Reforzado" (Maestría Nv. 10 Guardián).
   * @param {string} playerName - El nombre del jugador que usa la habilidad.
   */
  playGuardianShieldCosmetic(playerName) {
    if (!this.isEnabled) return;

    const playerPiece = document.querySelector(`.ficha-jugador[data-username="${playerName}"]`);
    if (!playerPiece) {
        console.warn(`[AnimSystem] No se encontró la ficha para ${playerName} (Escudo Reforzado).`);
        return;
    }

    // Crear el elemento de la animación
    const animElement = document.createElement('div');
    animElement.className = 'cosmetic-animation guardian-shield'; 
    
    // Posicionar el elemento (centrado en la ficha)
    const pieceRect = playerPiece.getBoundingClientRect();
    const pieceSize = playerPiece.offsetWidth;
    const animSize = 50; // Definido en el CSS
    
    animElement.style.left = `${pieceRect.left + (pieceSize / 2) - (animSize / 2)}px`;
    animElement.style.top = `${pieceRect.top + (pieceSize / 2) - (animSize / 2)}px`;

    document.body.appendChild(animElement); // Añadir al body

    // Limpiar después de 1.5s (la duración de la animación)
    setTimeout(() => {
        animElement.remove();
    }, 1500);
  }

  /**
   * Reproduce la animación "Doble Turno Etéreo" (Maestría Nv. 10 Estratega).
   * @param {string} playerName - El nombre del jugador que usa la habilidad.
   */
  playDoubleTurnCosmetic(playerName) {
    if (!this.isEnabled) return;

    const playerPiece = document.querySelector(`.ficha-jugador[data-username="${playerName}"]`);
    if (!playerPiece) {
        console.warn(`[AnimSystem] No se encontró la ficha para ${playerName} (Doble Turno).`);
        return;
    }

    // Crear el elemento de la animación
    const animElement = document.createElement('div');
    animElement.className = 'cosmetic-animation ethereal-echo';
    
    // Posicionar el elemento (exactamente donde está la ficha)
    const pieceRect = playerPiece.getBoundingClientRect();
    
    // Ajustar el tamaño para que coincida con la ficha
    animElement.style.width = `${playerPiece.offsetWidth}px`;
    animElement.style.height = `${playerPiece.offsetHeight}px`;
    
    animElement.style.left = `${pieceRect.left}px`;
    animElement.style.top = `${pieceRect.top}px`;
    
    // Heredar el color de fondo de la ficha original
    animElement.style.backgroundColor = playerPiece.style.backgroundColor;

    document.body.appendChild(animElement); // Añadir al body

    // Limpiar después de 0.6s (la duración de la animación)
    setTimeout(() => {
        animElement.remove();
    }, 600);
  }

  // Efecto de entrada para elementos
  fadeInElement(element, delay = 0) {
    if (!this.isEnabled || !element) return;
    
    element.style.opacity = '0';
    element.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
      element.style.transition = 'all 0.5s ease';
      element.style.opacity = '1';
      element.style.transform = 'translateY(0)';
    }, delay);
  }

  // Limpiar todas las animaciones activas
  cleanup() {
    this.confettiActive = false;
    
    // Remover elementos temporales
    const tempElements = document.querySelectorAll('.temp-game-piece, .confetti-piece, .particle, .victory-message');
    tempElements.forEach(el => el.remove());
    
    // Remover clases de animación
    const animatedElements = document.querySelectorAll('[class*="animate-"]');
    animatedElements.forEach(el => {
      el.className = el.className.replace(/animate-\w+/g, '').trim();
    });
  }

  // Obtener configuración de animaciones
  getSettings() {
    return {
      enabled: this.isEnabled,
      version: '1.0'
    };
  }
}