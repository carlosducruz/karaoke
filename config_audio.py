import sounddevice as sd
import numpy as np

class AudioConfig:
    @staticmethod
    def list_devices():
        """Lista todos os dispositivos de áudio disponíveis"""
        try:
            devices = sd.query_devices()
            print("\n" + "="*60)
            print("DISPOSITIVOS DE ÁUDIO DISPONÍVEIS")
            print("="*60)
            
            for i, device in enumerate(devices):
                input_channels = device.get('max_input_channels', 0)
                output_channels = device.get('max_output_channels', 0)
                
                if input_channels > 0 or output_channels > 0:
                    status = "✅ Padrão" if device.get('default_samplerate') else ""
                    print(f"\n[{i}] {device['name']} {status}")
                    print(f"   Entradas: {input_channels} | Saídas: {output_channels}")
                    print(f"   Taxa de amostragem: {device.get('default_samplerate', 'N/A')} Hz")
            
            print("\n" + "="*60)
            return devices
            
        except Exception as e:
            print(f"Erro ao listar dispositivos: {e}")
            return []
    
    @staticmethod
    def get_default_input_device():
        """Retorna o dispositivo de entrada padrão"""
        try:
            default_input = sd.default.device[0]
            if default_input is not None:
                device = sd.query_devices(default_input)
                return device
            return None
        except:
            return None
    
    @staticmethod
    def test_device(device_id=None, duration=2.0):
        """Testa um dispositivo de áudio"""
        try:
            samplerate = 44100
            channels = 2
            
            print(f"\n🎤 Testando dispositivo...")
            
            # Grava áudio
            recording = sd.rec(
                int(duration * samplerate),
                samplerate=samplerate,
                channels=channels,
                dtype='float32',
                device=device_id
            )
            sd.wait()
            
            # Analisa o áudio
            rms = np.sqrt(np.mean(recording**2))
            peak = np.max(np.abs(recording))
            
            print(f"✅ Teste concluído!")
            print(f"   RMS: {rms:.6f}")
            print(f"   Pico: {peak:.6f}")
            print(f"   Silêncio: {'SIM' if rms < 0.01 else 'NÃO'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro no teste: {e}")
            return False

if __name__ == "__main__":
    AudioConfig.list_devices()