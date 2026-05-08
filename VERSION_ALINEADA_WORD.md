# Documentacion tecnica alineada al Word (Capitulo 4)

## 1) Proposito del documento

Este documento explica como la implementacion del sistema web se alinea con el Capitulo 4 del informe
("Algoritmo"), donde se define el pseudocodigo y las funciones financieras del simulador de credito vehicular.

La meta de esta version no es solo listar funciones, sino documentar:

- la logica de calculo aplicada,
- los supuestos financieros usados,
- la trazabilidad entre teoria y codigo,
- y las validaciones necesarias para mantener resultados coherentes.

## 2) Alcance funcional de la implementacion

La aplicacion implementa un flujo completo de simulacion de credito vehicular:

1. Registro de datos del cliente, vehiculo y condiciones del prestamo.
2. Conversion de tasa ingresada a Tasa Efectiva Mensual (TEM).
3. Calculo de capital financiado y cuota base por metodo frances.
4. Generacion del cronograma periodo a periodo:
   - interes,
   - amortizacion,
   - saldo pendiente (capital vivo),
   - cuota total (incluyendo seguros y portes).
5. Construccion del flujo de caja del prestamo.
6. Calculo de indicadores financieros:
   - VAN,
   - TIR mensual,
   - TCEA anual equivalente.
7. Persistencia en base de datos SQLite para consulta posterior.

## 3) Supuestos del modelo financiero

Para asegurar consistencia con el informe y estabilidad del sistema, se aplican los siguientes supuestos:

- La tasa ingresada se recibe en decimal en backend (ejemplo: 12.5% -> 0.125).
- Si la tasa es nominal, se convierte primero a TEA y luego a TEM.
- La cuota base del metodo frances se calcula solo para meses "regulares" (plazo menos meses de gracia).
- La cuota total del periodo incluye costos adicionales:
  - seguro de desgravamen mensual,
  - seguro vehicular mensual,
  - portes fijos por cuota.
- Periodo de gracia:
  - gracia total: no se paga cuota y los intereses se capitalizan,
  - gracia parcial: se pagan intereses + seguros + portes, sin amortizacion de capital.
- El VAN se evalua con tasa mensual (TEM), porque el flujo es mensual.
- La TCEA se obtiene a partir de la TIR mensual: `TCEA = (1 + TIR_mensual)^12 - 1`.

## 4) Trazabilidad Capitulo 4 -> Codigo implementado

### 4.1 Conversion de tasa efectiva o nominal a TEM

- **Word (cap. 4.1):** convertir toda tasa a TEM.
- **Codigo:** `calcular_tasa_efectiva_mensual()`.
- **Resumen tecnico:**
  - tasa efectiva anual -> `TEM = (1 + TEA)^(1/12) - 1`
  - tasa nominal anual con capitalizacion `c` -> `TEA = (1 + j/c)^c - 1`, luego a TEM.

### 4.2 Capital financiado

- **Word (cap. 4.2):** monto financiado luego de descontar cuota inicial.
- **Codigo:** `calcular_capital_financiado()`.
- **Formula aplicada:** `S = PrecioVehiculo - CuotaInicial`.

### 4.3 Calculo de la cuota base (metodo frances)

- **Word (cap. 4.3):** cuota constante para cancelar el prestamo.
- **Codigo:** `calcular_cuota_base_metodo_frances()`.
- **Formula aplicada:** `C = S * r / (1 - (1 + r)^(-n))`.

### 4.4 Interes del periodo k

- **Word (cap. 4.4):** interes en funcion del saldo previo.
- **Codigo:** `calcular_interes_periodo_k()`.
- **Formula aplicada:** `I_k = Saldo_(k-1) * r`.

### 4.5 Amortizacion del periodo k

- **Word (cap. 4.5):** porcion de cuota que reduce capital.
- **Codigo:** `calcular_amortizacion_periodo_k()`.
- **Formula aplicada:** `A_k = C - I_k`.

### 4.6 Capital vivo al final del periodo k

- **Word (cap. 4.6):** saldo pendiente despues de amortizar.
- **Codigo:** `calcular_capital_vivo_final()`.
- **Formula aplicada:** `Saldo_k = Saldo_(k-1) - A_k`.

### 4.7 Cuota total del periodo k

- **Word (cap. 4.7):** cuota final incluyendo costos.
- **Codigo:** `calcular_cuota_total_periodo_k()`.
- **Formula aplicada:** `CuotaTotal_k = CuotaBase + Seguro_k + Portes`.

### 4.8 VAN

- **Word (cap. 4.8):** valor presente de los flujos.
- **Codigo:** `calcular_van()`.
- **Criterio aplicado:** descuento mensual sobre flujo mensual.

### 4.9 TIR

- **Word (cap. 4.9):** tasa que hace VAN = 0.
- **Codigo:** `calcular_tir()`.
- **Metodo numerico usado:**
  1. Newton-Raphson (rapido cuando converge),
  2. Biseccion como respaldo cuando hay inestabilidad de derivada.

### 4.10 TCEA

- **Word (cap. 4.10):** costo efectivo anual total.
- **Codigo:** `calcular_tcea_desde_tir_mensual()`.
- **Formula aplicada:** `TCEA = (1 + TIR_mensual)^12 - 1`.

### 4.11 Pseudocodigo consolidado

- **Word (cap. 4.11):** integracion del algoritmo completo.
- **Codigo:** `build_schedule()`.
- **Descripcion:** orquesta todo el flujo de calculo, genera cronograma y devuelve indicadores.

## 5) Flujo consolidado implementado

El flujo real del sistema se ejecuta en este orden:

1. Validar entradas (`precio`, `cuota inicial`, `plazo`, `gracia`).
2. Calcular capital financiado.
3. Convertir tasa a TEM.
4. Calcular cuota base del metodo frances.
5. Recorrer cada periodo `k`:
   - calcular interes,
   - aplicar regla de gracia (ninguna/parcial/total),
   - calcular amortizacion cuando corresponde,
   - actualizar saldo,
   - calcular cuota total del periodo,
   - agregar cuota al flujo de caja.
6. Calcular VAN, TIR y TCEA.
7. Retornar resultados y guardar en base de datos.

## 6) Estructura de salida del algoritmo

El algoritmo retorna un objeto `LoanResult` con:

- `tem`
- `cuota_base`
- `saldo_inicial`
- `schedule` (lista de `ScheduleRow`)
- `flujo`
- `van`
- `tir`
- `tcea`

Cada fila de cronograma (`ScheduleRow`) incluye:

- periodo,
- cuota_total,
- interes,
- amortizacion,
- saldo_final,
- seguro,
- portes.

## 7) Coherencia entre Word y sistema

La implementacion esta alineada con el capitulo 4 en terminos de formulas y orden de calculo.
Adicionalmente, agrega controles de robustez propios de software productivo:

- validaciones de rango,
- manejo de casos extremos (`tem = 0`, derivada cercana a cero en TIR),
- proteccion de saldo final no negativo,
- persistencia de resultados para trazabilidad.

Por lo tanto, el sistema no solo refleja el pseudocodigo academico, sino que lo convierte en una ejecucion
estable y verificable en entorno real.

## 8) Compatibilidad y mantenimiento

Se conservaron aliases para no romper compatibilidad con versiones previas del proyecto:

- `to_tem` -> `calcular_tasa_efectiva_mensual`
- `cuota_frances` -> `calcular_cuota_base_metodo_frances`
- `npv` -> `calcular_van`
- `irr` -> `calcular_tir`

Esto permite evolucionar la nomenclatura hacia el informe sin afectar integraciones existentes.

## 9) Recomendaciones para anexar en el informe final

Para fortalecer la sustentacion academica, se recomienda adjuntar:

1. Tabla de trazabilidad Capitulo 4 -> funcion Python (ya incluida arriba).
2. Capturas de un caso de prueba completo (entrada, cronograma, VAN/TIR/TCEA).
3. Comparacion de 2 escenarios:
   - sin periodo de gracia,
   - con gracia parcial o total.
4. Breve seccion de validacion numerica (tolerancia y redondeo usado).

Con esto, la documentacion queda en formato defendible tanto para revision tecnica como para rubrica academica.

## 10) Funciones implementadas (detalle tecnico)

Esta seccion documenta cada funcion principal del modulo `finance.py`, con su responsabilidad
especifica dentro del algoritmo.

### 10.1 `calcular_tasa_efectiva_mensual(tipo_tasa, tasa, capitalizacion=None) -> float`

- **Objetivo:** convertir la tasa ingresada a TEM.
- **Entradas:**
  - `tipo_tasa`: `"Efectiva"` o `"Nominal"`.
  - `tasa`: valor decimal de tasa (ej. `0.125`).
  - `capitalizacion`: frecuencia de capitalizacion para tasa nominal.
- **Salida:** `TEM` (decimal mensual).
- **Regla aplicada:**
  - efectiva -> `TEM = (1 + TEA)^(1/12) - 1`
  - nominal -> `TEA = (1 + j/c)^c - 1` y luego conversion a TEM.

### 10.2 `calcular_capital_financiado(precio_vehiculo, cuota_inicial_pct) -> float`

- **Objetivo:** obtener saldo inicial del prestamo.
- **Entradas:** precio del vehiculo y porcentaje de cuota inicial.
- **Salida:** capital financiado.
- **Formula:** `S = PrecioVehiculo - (PrecioVehiculo * cuotaInicialPct)`.

### 10.3 `calcular_cuota_base_metodo_frances(capital_financiado, tem, n) -> float`

- **Objetivo:** calcular cuota fija base del metodo frances.
- **Entradas:** saldo financiado, TEM y numero de periodos regulares.
- **Salida:** cuota base sin costos adicionales.
- **Formula:** `C = S * r / (1 - (1 + r)^(-n))`.

### 10.4 `calcular_interes_periodo_k(saldo_inicio_periodo, tem) -> float`

- **Objetivo:** calcular interes del periodo `k`.
- **Entradas:** saldo vivo al inicio del periodo y TEM.
- **Salida:** interes del periodo.
- **Formula:** `I_k = Saldo_(k-1) * r`.

### 10.5 `calcular_amortizacion_periodo_k(cuota_base, interes_periodo) -> float`

- **Objetivo:** calcular amortizacion del periodo `k`.
- **Entradas:** cuota base e interes del periodo.
- **Salida:** amortizacion del periodo.
- **Formula:** `A_k = C - I_k`.

### 10.6 `calcular_capital_vivo_final(saldo_inicio_periodo, amortizacion_periodo) -> float`

- **Objetivo:** actualizar capital vivo al cierre del periodo.
- **Entradas:** saldo inicial del periodo y amortizacion.
- **Salida:** nuevo saldo pendiente.
- **Formula:** `Saldo_k = Saldo_(k-1) - A_k`.

### 10.7 `calcular_cuota_total_periodo_k(cuota_base, seguro_periodo, portes) -> float`

- **Objetivo:** calcular pago total del periodo considerando costos.
- **Entradas:** cuota base, seguros y portes.
- **Salida:** cuota total.
- **Formula:** `CuotaTotal_k = CuotaBase + Seguro_k + Portes`.

### 10.8 `calcular_van(rate, flows) -> float`

- **Objetivo:** calcular VAN del flujo mensual.
- **Entradas:** tasa de descuento mensual y lista de flujos.
- **Salida:** valor actual neto.
- **Formula general:** `VAN = SUM(Flujo_t / (1 + r)^t)`.

### 10.9 `calcular_tir(flows, guess=0.01) -> float`

- **Objetivo:** hallar la tasa interna de retorno mensual.
- **Entradas:** lista de flujos y tasa inicial.
- **Salida:** TIR mensual.
- **Metodo:** Newton-Raphson con respaldo por biseccion.

### 10.10 `calcular_tcea_desde_tir_mensual(tir_mensual) -> float`

- **Objetivo:** convertir TIR mensual a costo anual equivalente.
- **Entrada:** TIR mensual.
- **Salida:** TCEA anual.
- **Formula:** `TCEA = (1 + TIR_mensual)^12 - 1`.

### 10.11 `build_schedule(...) -> LoanResult`

- **Objetivo:** ejecutar el algoritmo consolidado de simulacion.
- **Entradas:** parametros del cliente/credito (precio, tasa, plazo, gracia, seguros, portes).
- **Salida:** objeto `LoanResult` con:
  - `tem`, `cuota_base`, `saldo_inicial`,
  - `schedule` completo por periodos,
  - `flujo`, `van`, `tir`, `tcea`.
- **Rol en arquitectura:** funcion orquestadora principal invocada desde `app.py`.
