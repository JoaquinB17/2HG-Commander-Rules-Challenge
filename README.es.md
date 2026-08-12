# Two-Headed Giant Commander — buscador de duplas

*[English](README.md) · Español*

Un torneo local de Magic: The Gathering usaba el formato Two-Headed Giant (Gigante
de Dos Cabezas) en Commander, con una regla de la casa que convierte la construcción
de mazos en un problema de satisfacción de restricciones:

> Tú y tu compañero solo pueden usar comandantes impresos en el **mismo set de mazos
> precon** (cualquier impresión, original o reimpresión), y sus dos comandantes **no
> pueden compartir identidad de color**.

Nadie podía responder «¿qué puede jugar mi compañero?» sin cruzar listas de mazos a
mano. Este proyecto reconcilia dos APIs de cartas, deriva todas las duplas legales y
entrega la respuesta como un libro de Excel con una página de consulta interactiva.

**Resultado: 21.699 duplas legales** a partir de 1.055 cartas elegibles en 44 sets precon.

![La página Team Builder en Excel: dos celdas amarillas con un comandante y su
compañero, una línea de estado que dice "OK — legal partner pair (Doctor's companion).
15 choices for your partner", y debajo la tabla con cada compañero legal, sus colores,
la identidad resultante del equipo, el set precon compartido y en qué mazo
encontrarlo.](docs/team-builder.png)

📄 **Lee el caso de estudio** —
[Español](https://joaquinb17.github.io/2HG-Commander-Rules-Challenge/case-study.es.html) ·
[English](https://joaquinb17.github.io/2HG-Commander-Rules-Challenge/case-study.html) —
el problema, las tres decisiones que cambiaron la respuesta y cómo se testea una
planilla. También está el [texto en Markdown](docs/caso-de-estudio.md).

```bash
pip install -e ".[dev]"
python -m two_headed_giant
```

Genera `output/two_headed_giant_teams.xlsx`. Las respuestas de las APIs quedan en
caché en `data/`, así que las siguientes ejecuciones son offline y tardan segundos.

| Flag | Efecto |
| --- | --- |
| `--refresh` | Vuelve a descargar desde MTGJSON y Scryfall |
| `--include-unreleased` | Incluye mazos aún no publicados |
| `--singles-only` | Ignora las mecánicas de partner; un comandante por asiento |
| `--out RUTA` | Escribe el archivo en otra ubicación |

> **Nota sobre el idioma:** el libro de Excel está en inglés a propósito. Sus búsquedas
> dependen de que los nombres de las cartas coincidan exactamente con las listas de
> MTGJSON, así que traducirlos rompería todas las fórmulas.

## Arquitectura

```
two_headed_giant/
├── sources.py    descarga y cachea las listas de MTGJSON y el universo is:commander de Scryfall
├── rules.py      elegibilidad, mecánicas de partner, configuraciones de comandante, duplas legales
├── workbook.py   salida a Excel, incluida la página interactiva Team Builder
└── cli.py        conecta las etapas del pipeline
tests/
├── test_rules.py               23 tests unitarios, sin red ni libro de Excel
├── test_workbook.py            invariantes sobre las 21.699 filas generadas
└── test_team_builder_excel.py  maneja una instancia real de Excel vía COM
```

El pipeline es: listas de mazos ∩ cartas legales como comandante → pool por set →
configuraciones de comandante (un «asiento» es una carta, o dos que hacen partner
legalmente) → todas las parejas de colores disjuntos que comparten un set.

## Tres decisiones que vale la pena explicar

### 1. Listas de mazos, no pertenencia al set

El enfoque obvio —«toda carta legal como comandante cuyo set en Scryfall sea un set de
Commander»— es incorrecto, y de forma silenciosa. Esos códigos de set también cubren
Special Guests, cartas exclusivas de sobres o de coleccionista, y cartas de Jumpstart
que nunca estuvieron en un precon. Eso inflaba Marvel Super Heroes Commander de sus 88
comandantes elegibles reales a 251.

Por eso la elegibilidad sale de las **listas de mazos reales de MTGJSON**: una carta
cuenta solo si está físicamente entre las 100 del mazo. El mismo criterio *incluye*
correctamente cartas cuya impresión lleva el código del set principal, como las cartas
con código IKO dentro de un mazo de C20.

### 2. Delegar la regla en vez de reimplementarla

Al principio la elegibilidad era una prueba local: *criatura legendaria, o texto que
dice que puede ser tu comandante*. Es el tipo de regla que parece correcta y se pudre
en silencio. Cambios de reglas convirtieron a los **Vehículos** y las naves
(**Spacecraft**) legendarios en comandantes legales, y no llevan ese texto, así que
ninguna prueba basada en el texto podría encontrarlos.

Ahora la elegibilidad se delega en el filtro `is:commander` de Scryfall. El cambio
agregó 15 cartas y no quitó ninguna:

| Agregadas | Cantidad | Ejemplos |
| --- | --- | --- |
| Legendary Artifact — Vehicle | 12 | Shorikai, Weatherlight, Parhelion II, Esika's Chariot |
| Legendary Artifact — Spacecraft | 2 | Hearthhull the Worldseed, Inspirit Flagship Vessel |
| Legendary Planeswalker | 1 | Grist, the Hunger Tide |

Grist es la señal de que la regla local ya era poco sólida por sí sola, más allá de
cualquier cambio de reglas: es una carta de criatura en todas partes menos en el campo
de batalla, siempre fue un comandante legal, y la prueba basada en texto la descartaba
sin avisar.

Los **Backgrounds** son el único caso que todavía necesita lógica propia: cumplen
`is:commander` pero solo pueden ser un *segundo* comandante.

### 3. Las mecánicas de partner salen del texto de Oracle, no de `keywords`

El campo `keywords` de Scryfall reporta un `Partner` simple en cartas que en realidad
tienen una variante *restringida*. Toda carta con `Partner with [nombre]` viene marcada
como `Partner`, y lo mismo pasa con `Partner—Character select`. Construir sobre ese
campo haría que Pir fuera un partner legal de Thrasios, algo que los rulings prohíben
explícitamente:

> una criatura con la habilidad «partner with» no puede hacer partner con ninguna
> criatura que no sea la designada

Por eso las mecánicas se parsean desde el texto de Oracle, y `test_rules.py` fija cada
combinación ilegal de forma directa.

| Mecánica | Hace dupla con | Unidades |
| --- | --- | --- |
| `Partner` | cualquier otra carta con Partner simple | 116 |
| `Partner with [nombre]` | **solo** la carta que nombra | 14 |
| `Partner—Character select` | solo otras cartas con Character select | 15 |
| `Doctor's companion` | cualquier Time Lord Doctor legendario | 390 |
| `Choose a Background` | cualquier Background | 16 |

## El libro de Excel

**Team Builder** es la página que se abre primero. Escribes tu comandante (y una
segunda carta si vas con una dupla de partner) y lista todos los comandantes que tu
compañero puede traer legalmente, con el set compartido y en qué mazo encontrarlo. Una
línea de estado separa tres situaciones que de otro modo se ven idénticas: *legal*,
*hacen partner pero nunca se imprimieron juntos*, y *no pueden hacer partner*.

Otras hojas: `Rules`, `Sets`, `Decks`, `Commanders`, `Partner Pairs`, `Teams` y
`Not Eligible` (cartas legendarias en precons que **no** son comandantes legales, con
el motivo, para que las exclusiones se puedan auditar en vez de quedar invisibles).

**Las fórmulas se limitan a `INDEX`/`MATCH`.** `FILTER`, `XLOOKUP` y `SORT` son
«funciones futuras» que deben escribirse como `_xlfn._xlws.FILTER` cuando el archivo se
genera fuera de Excel, y aparecen como `#NAME?` si el prefijo está mal. Evitarlas
además mantiene el libro funcionando en versiones antiguas de Excel y en Google Sheets,
donde está verificado.

Las búsquedas también son baratas por diseño: la lista de compañeros resuelve la
posición de su bloque con **un** `MATCH` y luego lee 469 filas por desplazamiento. Un
`MATCH` por fila reescanearía una tabla de 43.000 filas en cada pulsación de tecla.

## Testing

```bash
pytest
```

En un clon nuevo esto reporta **23 passed, 32 skipped**, y es el resultado esperado.
Solo la capa unitaria es autocontenida; las otras dos se omiten limpiamente hasta que
existan sus prerrequisitos:

| Capa | Necesita |
| --- | --- |
| `test_rules.py` | nada — corre en cualquier parte en 0,1s |
| `test_workbook.py` | el libro generado (`python -m two_headed_giant`) |
| `test_team_builder_excel.py` | el libro, más Windows con Excel y pywin32 |

55 tests en tres capas:

- **`test_rules.py`** — funciones puras, sin E/S, 0,1 s. Fija la matriz de legalidad de
  partner, incluidas las combinaciones que **no** deben ser legales.
- **`test_workbook.py`** — invariantes sobre las 21.699 duplas generadas, validadas
  contra las listas de mazos de origen y no contra el estado intermedio del propio
  build, para que un bug no pueda avalarse a sí mismo.
- **`test_team_builder_excel.py`** — abre el libro en una instancia real de Excel vía
  COM, escribe en las celdas de entrada, fuerza el recálculo y compara lo que Excel
  calcula contra lo que dicen los datos. openpyxl escribe fórmulas pero nunca las
  evalúa, así que un error de índice en un `INDEX` pasaría desapercibido. Se omite
  limpiamente sin Windows ni Excel.

## Hallazgos

Bajo la regla de la casa, algunos sets casi no funcionan:

| Set | Comandantes | Sin compañero legal | Duplas legales |
| --- | --- | --- | --- |
| Phyrexia: All Will Be One (`ONC`) | 7 | **7** | **0** |
| Lorwyn Eclipsed (`ECC`) | 17 | 10 | 7 |
| Modern Horizons 3 (`M3C`) | 19 | 6 | 34 |

`ONC` no tiene ninguna dupla legal: todas sus identidades de color contienen rojo o
blanco. Lorwyn Eclipsed tiene 17 comandantes pero solo 7 duplas: cuatro son de cinco
colores y el set no tiene ningún comandante incoloro, así que se quedan sin opciones.
La hoja `Sets` muestra esto set por set, y conviene revisarla antes de comprometerse
con uno.

## Fuentes de datos

- [MTGJSON](https://mtgjson.com) — listas de mazos precon
- [Scryfall](https://scryfall.com) — el universo `is:commander` y todos los datos de cartas

Ambas se consultan con una pausa entre peticiones, según sus guías publicadas.
