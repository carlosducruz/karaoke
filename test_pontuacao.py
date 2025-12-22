"""
Script de teste para verificar sistema de pontuação
"""
import tkinter as tk
from karaoke_player import KaraokePlayer

if __name__ == "__main__":
    root = tk.Tk()
    app = KaraokePlayer(root)
    
    print("\n" + "="*60)
    print("TESTE DO SISTEMA DE PONTUAÇÃO KARAOKE")
    print("="*60)
    print("\n📋 INSTRUÇÕES:")
    print("1. Carregue um arquivo MP4")
    print("2. Aperte PLAY")
    print("3. Cante junto com a música!")
    print("4. Ao final, você verá sua pontuação")
    print("\n💡 DICA: Quanto mais você cantar junto com o ritmo,")
    print("   maior será sua pontuação!")
    print("="*60 + "\n")
    
    root.mainloop()
