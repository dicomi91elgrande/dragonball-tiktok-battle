# Dragon Ball TikTok Battle

Overlay para directos de TikTok: dos personajes de Dragon Ball se enfrentan y el
chat les da **energía con regalos**. Al alcanzar ciertos umbrales el personaje
**se transforma** (Base → Super Saiyan → SS2 → SS3 → God → Blue → Ultra Instinct).
Cuando el temporizador llega a cero, gana quien tenga más energía.

Misma arquitectura que `pokemon-tiktok-battle`:

```
TikFinity (regalo/chat) --POST--> /webhook --SSE--> overlay (index.html) en OBS
```

## Arrancar en local

```bash
cd dragonball-tiktok-battle
python server.py
```

- Overlay: http://localhost:3000/
- Overlay limpio para OBS (sin panel de pruebas): http://localhost:3000/?obs=1
- WebHook para TikFinity: http://localhost:3000/webhook

El **panel "Simulador"** (arriba a la derecha) permite probarlo sin TikTok:
elegir personajes, sumar energía y arrancar el temporizador.
Atajos de teclado: `0` oculta/muestra el simulador, `R` resetea.

## Cómo se juega (mecánica)

1. Un espectador escribe el nombre de un personaje en el chat → ese personaje
   **sale a luchar** (primer hueco libre: izquierda, luego derecha).
2. Cualquier **regalo** suma energía al lado del usuario que lo manda.
   - Si el usuario ya eligió bando (comentó un personaje), su regalo va a ese lado.
   - Si no, el regalo refuerza al que va **por detrás** (para que la pelea esté reñida).
3. Cada transformación **multiplica** la energía que entra (ver `LADDERS` en `index.html`),
   así hay remontadas.
4. Al llegar el temporizador a 0 → pantalla de **ganador**.

Umbrales por defecto (saiyans): SS1 = 100, SS2 = 500, SS3 = 1000, God = 2000,
Blue = 3500, Ultra Instinct = 6000. Se editan en `LADDERS` dentro de `index.html`.

## Aspecto: monigote con la foto de perfil

Cada luchador es un **monigote chibi dibujado en SVG** (no se usan sprites con
copyright): cuerpo de artista marcial con el gi del color de su equipo, y de
**cabeza la foto de perfil de TikTok** del usuario que está en ese lado,
recortada en círculo. Al transformarse le **crece el pelo Super Saiyan** y cambia
de color según la fase (negro → dorado → rojo God → azul Blue → plateado Ultra
Instinct), con aura, partículas y rayos.

Ventajas: cero problemas de derechos (es arte propio) y mucho más enganche, porque
los espectadores luchan literalmente con su propia cara.

- La foto la trae el servidor por su proxy `/avatar` a partir del avatar que manda
  TikFinity en el evento (`imgprofile`/`profilePicture`/…). Si no hay foto, sale la
  inicial del nombre dentro del círculo.
- El cuerpo del monigote es la función `monigoteSVG()` en `index.html`: ahí puedes
  cambiar la forma del cuerpo, el pelo, los guantes, etc. sin tocar el resto.
- Tamaño/color del pelo y color del gi por fase se controlan en `renderSide()`.

Si algún día quisieras volver a sprites de imagen, se puede añadir como capa extra,
pero el monigote evita el riesgo de retiradas por copyright en TikTok.

## Añadir o cambiar personajes

- Reconocimiento del nombre en el chat: edita `CHARACTERS` en `server.py`
  (nombre canónico + alias). La búsqueda es difusa, no hace falta escribirlo exacto.
- Transformaciones, colores de aura y multiplicadores: `LADDERS` en `index.html`.
- A qué escalera pertenece cada personaje y su color de equipo: `ROSTER` en `index.html`.

## Desplegar en Render

Igual que el de Pokémon: repo en GitHub + Blueprint con `render.yaml` (plan free).
El webhook queda en `https://<tu-servicio>.onrender.com/webhook` y el overlay en
`https://<tu-servicio>.onrender.com/?obs=1`. El plan free duerme tras 15 min.
Token opcional con la variable de entorno `HOOK_TOKEN`.
