# Dragon Ball TikTok Battle Launcher

Este lanzador abre el overlay en una ventana independiente de Edge o Chrome, en modo app y sin barra de navegador.

## Compilar

```powershell
cd C:\Users\Usuario\Documents\claude\dragonball-tiktok-battle
powershell -ExecutionPolicy Bypass -File .\launcher\build-launcher.ps1
```

El ejecutable queda en:

```text
C:\Users\Usuario\Documents\claude\dragonball-tiktok-battle\launcher\bin\DragonBallTikTokBattle.exe
```

## Cambiar URL

Edita este archivo:

```text
C:\Users\Usuario\Documents\claude\dragonball-tiktok-battle\launcher\bin\launcher-config.txt
```

Por defecto usa:

```text
url=https://dragonball-tiktok-battle.onrender.com/?obs=1&stream=band
```

Tamano horizontal recomendado para TikTok/OBS:

```text
width=1280
height=720
scale=1
```
