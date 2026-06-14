# Fase 2 — Analytics: las cuentas, verificadas a mano

## El problema que resolvía

Esta es la fase que decide si el proyecto vale. Un reclutador puede perdonar una
UI mejorable; no perdona una métrica financiera mal calculada. Necesitaba un
motor de métricas en el que pudiera *confiar*, y poder demostrar por qué confío:
no porque "el test pasa", sino porque el número esperado lo calculé a mano,
aparte, y coincide.

## La decisión de arquitectura: funciones puras, cero base de datos

Todo el motor de analytics son **funciones puras** sobre arrays de numpy y
Series de pandas. Ninguna toca la base. ¿Por qué? Porque eso las hace triviales
de testear y razonar: entrada → salida, sin estado, sin mocks de DB. La capa de
servicio (Fase 3) va a alimentarlas desde silver; acá viven solas y limpias.

Las separé por responsabilidad: `returns` (rendimiento total, acumulado,
time-weighted), `risk` (volatilidad, drawdown, Sharpe, beta), `exposure`
(sector/país/moneda + concentración Herfindahl y top-N), `correlation` (matriz
para detectar falsa diversificación) y `portfolio` (el orquestador que arma
snapshots de posición y la serie de valor).

## La técnica: TDD con números calculados por fuera

Cada test financiero lleva el cálculo a mano en el comentario. Ejemplo, el
drawdown:

```python
# prices 100, 120, 90, 110. running max 100,120,120,120.
# drawdowns: 0, 0, 90/120-1 = -0.25, 110/120-1 = -0.0833
# max drawdown = -0.25
assert max_drawdown([100, 120, 90, 110]) == pytest.approx(-0.25)
```

Y el beta, donde el truco lindo es que el factor `/(n-1)` se cancela entre
covarianza y varianza:

```python
# cov_num = 0.0007 ; var_num = 0.0005 -> beta = 0.0007/0.0005 = 1.4
assert beta([0.02,-0.01,0.03,0.00], [0.01,-0.01,0.02,0.00]) == pytest.approx(1.4)
```

**La anécdota honesta:** mi primer test de Sharpe falló. No porque la función
estuviera mal, sino porque me equivoqué multiplicando a mano en el comentario
(puse 41.247 en vez de 41.243). Lo lindo es que ese error *es la prueba de que
la verificación a mano es real*: si solo hubiera escrito `== sharpe_ratio(...)`,
nunca lo habría detectado, porque el test siempre pasa contra sí mismo. El
cálculo independiente es justamente lo que atrapa el error — en este caso, el mío.

## La alternativa que descarté: anualizar con desvío poblacional

Podría haber usado `ddof=0` (desvío poblacional). Elegí `ddof=1` (muestral,
insesgado) y lo mantuve **consistente** en volatilidad, Sharpe y beta. Mezclar
ddof entre métricas es una fuente clásica de números que "casi" cierran. Quedó
en un ADR junto con la convención de 252 días y la definición de Sharpe.

## La decisión que documenté para que no se lea como bug

`portfolio_value_series` aplica las cantidades de *hoy* a toda la historia de
precios: es un backtest del basket actual, ideal para métricas de riesgo (el
riesgo de lo que tengo hoy), pero no es mi P&L realizado (que depende del timing
de entrada). Esa distinción es exactamente lo que un entrevistador va a pinchar,
así que la dejé escrita en un ADR en vez de implícita. La serie realizada que
respeta `opened_at` queda como V2 en el roadmap.

## Antes / después

- **Antes:** datos en la base, ninguna lectura sobre ellos.
- **Después:** 5 módulos de analytics, **47 tests en verde**, cada métrica
  financiera con su valor esperado derivado a mano. El motor está listo para que
  la Fase 3 lo conecte a los datos reales del seed.

## Criterios de aceptación cumplidos

- [x] `pytest` verde (47 tests).
- [x] Cada métrica financiera con test de caso conocido calculado a mano.
- [x] Casos borde cubiertos: series vacías/cortas/constantes → 0.0, sin
      NaN/inf silenciosos.
- [ ] *(Pendiente Fase 3)* test de integración sobre el seed real:
      `beta(SPY, SPY) ≈ 1`, drawdown ≤ 0, pesos suman 1.
