/**
 * AeroGuard — Tactical Audio Siren Service (Web Audio API)
 * Genera alertas sonoras tácticas sintetizadas militarmente en tiempo real
 * sin necesidad de archivos de audio externos (.mp3/.wav).
 */

export class TacticalAudioSiren {
  constructor() {
    this.audioCtx = null;
    this.currentOscillator = null;
    this.currentGain = null;
    this.alarmTimer = null;
    this.cadenceInterval = null;
    this.isPlaying = false;
    
    // Persistencia de Mute en localStorage
    this.muted = localStorage.getItem('aeroguard_audio_mute') === 'true';
    
    // Auto-desbloqueo de AudioContext con la primera interacción del usuario
    this._bindUnlockAudio();
  }

  _bindUnlockAudio() {
    const unlock = () => {
      this._ensureAudioContext();
      if (this.audioCtx && this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }
      window.removeEventListener('click', unlock);
      window.removeEventListener('keydown', unlock);
    };
    window.addEventListener('click', unlock, { once: true });
    window.addEventListener('keydown', unlock, { once: true });
  }

  _ensureAudioContext() {
    if (!this.audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        this.audioCtx = new AudioContextClass();
      }
    }
    return this.audioCtx;
  }

  isMuted() {
    return this.muted;
  }

  toggleMute() {
    this.setMuted(!this.muted);
    return this.muted;
  }

  setMuted(muted) {
    this.muted = Boolean(muted);
    localStorage.setItem('aeroguard_audio_mute', this.muted ? 'true' : 'false');
    if (this.muted && this.isPlaying) {
      this.stop();
    }
  }

  /**
   * Dispara sirena bitonal táctica (880Hz / 1320Hz alternante cada 220ms)
   * @param {Object} options
   * @param {number} options.durationMs - Duración total (ej: 2500ms o 0 para indefinido)
   * @param {number} options.gain - Volumen (default 0.15 para evitar saturación)
   */
  playAlert({ durationMs = 2200, gain = 0.15 } = {}) {
    if (this.muted) return;

    try {
      const ctx = this._ensureAudioContext();
      if (!ctx) return;

      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      this.stop(); // Detener cualquier reproducción previa

      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gainNode = ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(880, now);

      // Suave ataque para evitar chasquido 'pop'
      gainNode.gain.setValueAtTime(0.001, now);
      gainNode.gain.exponentialRampToValueAtTime(gain, now + 0.05);

      osc.connect(gainNode);
      gainNode.connect(ctx.destination);

      osc.start(now);

      this.currentOscillator = osc;
      this.currentGain = gainNode;
      this.isPlaying = true;

      // Bitonal switching: 880 Hz / 1320 Hz cada 220ms
      let stateHi = false;
      this.cadenceInterval = setInterval(() => {
        if (!this.isPlaying || !this.currentOscillator) return;
        stateHi = !stateHi;
        const freq = stateHi ? 1320 : 880;
        try {
          this.currentOscillator.frequency.setValueAtTime(freq, ctx.currentTime);
        } catch (e) {
          // Context cerrado o ya destruido
        }
      }, 220);

      // Auto-apagado tras durationMs
      if (durationMs > 0) {
        this.alarmTimer = setTimeout(() => {
          this.stop();
        }, durationMs);
      }
    } catch (err) {
      console.warn('[TacticalAudioSiren] Error al generar audio:', err);
    }
  }

  /**
   * Ejecuta ráfaga táctica de prueba de 1.5 segundos
   */
  testSiren() {
    const wasMuted = this.muted;
    if (wasMuted) {
      // Temporalmente desmutea para la prueba explícita del botón
      this.muted = false;
    }
    this.playAlert({ durationMs: 1500, gain: 0.15 });
    if (wasMuted) {
      setTimeout(() => {
        this.muted = true;
      }, 1600);
    }
  }

  /**
   * Detiene de inmediato la sirena y libera nodos
   */
  stop() {
    this.isPlaying = false;
    if (this.cadenceInterval) {
      clearInterval(this.cadenceInterval);
      this.cadenceInterval = null;
    }
    if (this.alarmTimer) {
      clearTimeout(this.alarmTimer);
      this.alarmTimer = null;
    }

    if (this.currentGain && this.audioCtx) {
      try {
        const now = this.audioCtx.currentTime;
        this.currentGain.gain.setValueAtTime(this.currentGain.gain.value, now);
        this.currentGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.05);
      } catch (e) {}
    }

    if (this.currentOscillator) {
      try {
        this.currentOscillator.stop(this.audioCtx ? this.audioCtx.currentTime + 0.06 : 0);
        this.currentOscillator.disconnect();
      } catch (e) {}
      this.currentOscillator = null;
    }

    this.currentGain = null;
  }
}

// Instancia única compartida
export const tacticalAudio = new TacticalAudioSiren();
