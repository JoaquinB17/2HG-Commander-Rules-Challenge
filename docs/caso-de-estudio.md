# El Dilema de los Gigantes

Magic: The Gathering es un juego de cartas complejo y tiene muchas formas de jugarse.
Para que se entienda el dilema que enfrentaba un torneo local, voy a definir un par de
cosas de la forma más sencilla posible.

## Lo mínimo que hay que saber

> **Nota sobre lo incoloro.** Además de los cinco colores existe una sexta posibilidad
> que no es un color: las cartas **incoloras**, marcadas con **C**. Un comandante
> incoloro puede acompañar a cualquier mazo con color, incluso a uno de cinco colores.
> Lo que *no* puede es emparejarse con otro incoloro: el torneo trata la ausencia de
> color como una identidad propia, así que dos incoloros la comparten. Son 34
> combinaciones que a primera vista parecen válidas y no lo son.

El juego se define por su sistema de **colores**: Blanco, Azul, Negro, Rojo y Verde.
En inglés son White, Blue, Black, Red y Green, y de aquí en adelante voy a usar
**W U B R G** para referirme a cada uno (la U es por bl**U**e, porque la B ya se la
llevó Black). Los colores representan distintos tipos de magia y de criaturas, y al
mismo tiempo funcionan como una limitante.

Entra **Commander**, una forma de jugar donde eliges un "comandante" que representa a
tu mazo y que define a qué colores tienes acceso. Por ejemplo: si tu comandante es
"Mooriel, la Vaca Guerrera" y ella es blanca y negra, solo puedes usar cartas de esos
dos colores. Te cierra los otros tres. Además no puedes repetir cartas —una sola copia
de cada una, salvo las tierras básicas—. Es una limitante que invita a la creatividad.

El formato se volvió tan popular en parte gracias a los **mazos preconstruidos**:
mazos diseñados para jugarse directamente, sin cambios, apenas los sacas de la caja.

## El torneo

Aquí es donde se pone complicado. El torneo usaba el formato **Gigante de Dos Cabezas**
(*Two-Headed Giant*), que es como se conoce oficialmente al juego por equipos: 2 contra
2. Y este torneo quería ser único en cómo se formaban los equipos, con dos reglas que
convierten la elección de compañero en un dolor de cabeza:

**Regla 1 — Tú y tu compañero no pueden compartir colores.** Si mi mazo usa todos los
colores menos el azul, entonces el mazo de mi compañero tiene que ser azul y nada más.

No es ciencia espacial. Es sencillo, y no necesita ninguna solución especial.

**Regla 2 — Ambos comandantes deben haber aparecido en el mismo mazo preconstruido.**

Y aquí está el problema.

## El tamaño del problema

Al momento de escribir esto hay **44 sets** de mazos preconstruidos legales publicados
desde 2011, con un total de **159 mazos** individuales. Cada uno trae 100 cartas, así
que estamos mirando **15.900 espacios de carta** —unas **6.012 cartas distintas** una
vez que descuentas todo lo que se repite entre mazos—.

Para decidir si una dupla es legal o no, primero hay que responder cuatro preguntas:

1. ¿De dónde saco los datos de estas cartas?
2. ¿Cuántas de estas cartas pueden ser comandantes?
3. ¿Hay casos especiales?
4. ¿Cuántas duplas legales existen?

## Las primeras dos preguntas

Se responden con dos herramientas poderosas: **MTGJSON** y **Scryfall**. Magic es un
juego tan popular que ha motivado la creación de herramientas para seguirle la pista a
reglas, historia, cartas, ediciones y colecciones.

MTGJSON mantiene una base de datos con las listas de los mazos preconstruidos, listas
para examinar: esa va a ser nuestra lista de cartas. Scryfall es la base de datos más
completa del juego, y nos va a servir para determinar los colores y para saber qué
cartas pueden ser comandantes.

La mejor forma es tomar las cartas de los mazos y pasarlas por el filtro
**`is:commander`** de Scryfall. Según las reglas, un comandante debe ser:

- una **criatura, estación o vehículo legendario**, o
- una carta tipo **planeswalker** que diga explícitamente "puede ser tu comandante".

Si uno buscara a mano con esos dos criterios, se encontraría con excepciones. La más
notoria es **Grist, the Hunger Tide**, que legalmente es un comandante pero no cumple
ni con el primer criterio ni con el segundo. No voy a entrar en detalles, pero Grist es
un dolor de cabeza dentro de las reglas por cómo está redactada, y precisamente por eso
**no** usar `is:commander` la dejaría fuera sin que uno se diera cuenta.

Con el filtro aplicado, el total queda en **1.055 comandantes posibles**.

## La tercera pregunta: los casos especiales

Y aquí se pone todavía más complejo.

Normalmente tienes un solo comandante, pero hay cartas que te dejan tener **dos**. Y
dependiendo de cuál sea la mecánica, la cosa se complica.

**Partner.** Cartas que puedes emparejar libremente entre ellas. Hay **27** en los
preconstruidos, y como cada una puede ser de hasta 2 colores, una dupla puede llegar a
4 colores.

**Partner with.** Cartas que tienen un compañero muy específico, listado en la propia
carta. Mucho más sencillo de manejar: cada una tiene exactamente una pareja posible.

**Doctor's companion.** Introducida en el set de Doctor Who. Deja que una carta con esa
habilidad sea tu segundo comandante si tu comandante principal es un *Time Lord Doctor*.
Son 41 cartas en total: **15 doctores** y **26 compañeros**.

**Choose a Background.** Aplica a **4 criaturas** que pueden emparejarse con **4 cartas**
que definen su trasfondo.

**Character select.** **6 criaturas** que puedes emparejar entre sí.

### Dónde la regla 2 muerde de verdad

Aquí está lo interesante, y es lo que hace que este problema no se pueda resolver
multiplicando en una servilleta.

Doctor's companion vive entero dentro de un set (Doctor Who). Character select vive
entero en otro (Tortugas Ninja). Los Backgrounds, en Baldur's Gate. Como cada mecánica
está contenida en un solo set, la regla del "mismo mazo preconstruido" no elimina nada,
y multiplicar da el número correcto:

| Mecánica | Cuentas | Duplas legales |
| --- | --- | --- |
| Doctor's companion | 15 doctores × 26 compañeros | **390** |
| Choose a Background | 4 criaturas × 4 trasfondos | **16** |
| Character select | 6 criaturas entre sí | **15** |
| Partner with | cada una con su única pareja | **14** |

**Partner es la excepción**, y por eso es la interesante. Sus 27 cartas están repartidas
en **10 sets distintos**. Si todas combinaran con todas serían **351 duplas**. Pero la
regla 2 exige que ambas hayan salido en el mismo preconstruido, y eso las deja en
**116**.

De hecho, 105 de esas 116 vienen de un solo producto: **Commander 2016**, que por sí
solo trae 15 cartas con Partner. Las otras 11 salen repartidas entre los nueve sets
restantes.

En total: **551 duplas de partner** legales.

### Por qué Commander 2016 es el mejor producto del torneo

Vale la pena detenerse en C16, porque no solo aporta la mayor cantidad de duplas: son
también las **más flexibles**, y eso importa muchísimo cuando la regla 1 te obliga a
no pisarle los colores a tu compañero.

Sus 15 cartas con Partner son **todas exactamente de dos colores**, y entre ellas cubren
**las diez combinaciones de dos colores que existen** en el juego. Ninguna se repite en
el sentido de dejar un hueco: están las diez.

El efecto se nota al contar identidades de color. Las 105 duplas de C16 alcanzan
**20 identidades distintas**, más que cualquier otro set del torneo. Doctor Who, con casi
cuatro veces más duplas, solo llega a 14:

| Set | Duplas | Identidades de color distintas |
| --- | --- | --- |
| Commander 2016 | 105 | **20** |
| Doctor Who | 392 | 14 |
| Baldur's Gate | 17 | 13 |
| Tortugas Ninja | 16 | 8 |

De esas 105 duplas, 65 llegan a tres colores y 35 llegan a cuatro. Es decir: con C16
puedes armar un mazo de cuatro colores y dejarle a tu compañero un único color, o
repartirse tres y dos. Casi cualquier reparto que se les ocurra tiene una dupla que lo
soporta.

Y como dato curioso, esa flexibilidad viene acompañada de poder bruto. Los partners de
C16 —**Thrasios, Triton Hero**, **Tymna the Weaver**, **Vial Smasher the Fierce**,
**Kraum, Ludevic's Opus**— son cartas básicas del Commander competitivo desde hace años;
la dupla Thrasios + Tymna es probablemente la más conocida del formato. Wizards imprimió
un producto pensado para que las cartas se combinaran entre sí, y una década después
resulta ser exactamente lo que este torneo premia.

## La cuarta pregunta

Sumando todo, un "asiento" en un equipo no es una carta: es **una carta o una dupla
legal**. Eso da **1.602 configuraciones posibles** de comandante.

Y recién ahí se puede responder la pregunta original, cruzando cada configuración
contra todas las demás y filtrando por las dos reglas:

> **21.699 duplas legales.**

De esas, 11.534 son un comandante por lado, y 10.165 involucran al menos una dupla de
partner.

## Lo que apareció al final

Cuando por fin puedes enumerar todas las duplas, aparece algo que nadie había notado:
el formato es **muy** disparejo.

| Set | Comandantes | Sin compañero posible | Duplas legales |
| --- | --- | --- | --- |
| Phyrexia: All Will Be One | 7 | 7 | **0** |
| Lorwyn Eclipsed | 17 | 10 | 7 |
| Modern Horizons 3 | 19 | 6 | 34 |
| Doctor Who | 78 | 0 | 10.582 |

*Phyrexia: All Will Be One* no tiene **ninguna** dupla legal: todas las identidades de
color de ese set contienen rojo o blanco, así que nada puede emparejarse con nada.
Lorwyn Eclipsed tiene 17 comandantes pero solo 7 duplas, porque cuatro de ellos son de
cinco colores y el set no trae ningún comandante incoloro que los acompañe.

Es exactamente el tipo de cosa que arruina un torneo: alguien compra un producto,
arma su mazo, y descubre en la mesa que su compañero no tiene ninguna opción legal.

## Y ahora, cómo se lo comunico a la gente

Los jugadores no van a correr un script. Así que el resultado final es un **libro de
Excel**: escribes tu comandante y te lista todos los comandantes que tu compañero puede
elegir legalmente, con el set que los hace válidos y en qué mazo encontrar cada uno.

La respuesta completa, en una planilla que se abre en dos clics.
