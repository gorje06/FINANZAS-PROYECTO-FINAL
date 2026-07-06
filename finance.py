"""
Motor financiero: conversión a TEM, método francés, Compra Inteligente (cuota balón),
gracias, costos iniciales, VAN/TIR/TCEA (perspectiva del deudor).
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import List


MODALIDAD_CONVENCIONAL = "Convencional"
MODALIDAD_COMPRA_INTELIGENTE = "Compra Inteligente"


@dataclass
class ScheduleRow:
    periodo: int
    cuota_total: float
    interes: float
    amortizacion: float
    saldo_final: float
    seguro: float
    portes: float
    cuota_balon: float = 0.0


@dataclass
class LoanResult:
    tem: float
    cuota_base: float
    saldo_inicial: float
    schedule: List[ScheduleRow]
    flujo: List[float]
    van: float
    tir: float
    tcea: float
    modalidad: str
    cuota_balon_monto: float
    cuota_inicial_monto: float
    gastos_iniciales: float
    capital_amortizable: float


def calcular_tasa_efectiva_mensual(
    tipo_tasa: str,
    tasa: float,
    capitalizacion: int | None = None,
    periodo_tasa: int = 7,
) -> float:
    """Conversión de tasa efectiva (por periodo) o nominal a TEM mensual."""
    if tasa <= 0:
        raise ValueError("La tasa debe ser mayor a 0.")

    tipo = tipo_tasa.lower().strip()
    if tipo == "efectiva":
        p = periodo_tasa
        if p == 0:
            return (1 + tasa) ** 30 - 1
        if p == 1:
            return (1 + tasa) ** 2 - 1
        if p == 2:
            return tasa
        if p == 3:
            return (1 + tasa) ** (1 / 2) - 1
        if p == 4:
            return (1 + tasa) ** (1 / 3) - 1
        if p == 5:
            return (1 + tasa) ** (1 / 4) - 1
        if p == 6:
            return (1 + tasa) ** (1 / 6) - 1
        return (1 + tasa) ** (1 / 12) - 1
    if tipo == "nominal":
        c = capitalizacion or 12
        if c <= 0:
            raise ValueError("La capitalizacion debe ser mayor a 0.")
        tea = (1 + tasa / c) ** c - 1
        return (1 + tea) ** (1 / 12) - 1
    raise ValueError("tipo_tasa debe ser 'Efectiva' o 'Nominal'.")


def calcular_cuota_inicial_monto(precio_vehiculo: float, cuota_inicial_pct: float) -> float:
    return precio_vehiculo * (cuota_inicial_pct / 100.0)


def calcular_capital_financiado(precio_vehiculo: float, cuota_inicial_pct: float) -> float:
    """Capital financiado = precio menos cuota inicial (%)."""
    if precio_vehiculo <= 0:
        raise ValueError("El precio del vehiculo debe ser mayor a 0.")
    if not (0 <= cuota_inicial_pct < 100):
        raise ValueError("La cuota inicial debe estar entre 0 y 100.")
    return precio_vehiculo - calcular_cuota_inicial_monto(precio_vehiculo, cuota_inicial_pct)


def calcular_capital_financiado_total(
    precio_vehiculo: float,
    cuota_inicial_pct: float,
    gastos_notariales: float = 0.0,
    gastos_registrales: float = 0.0,
    costos_iniciales: float = 0.0,
) -> float:
    """Saldo desembolsado: capital del vehículo + gastos notariales/registrales financiados."""
    base = calcular_capital_financiado(precio_vehiculo, cuota_inicial_pct)
    gastos = max(gastos_notariales, 0) + max(gastos_registrales, 0) + max(costos_iniciales, 0)
    return base + gastos


def calcular_cuota_balon_monto(precio_vehiculo: float, cuota_balon_pct: float) -> float:
    """Cuota balón = porcentaje del valor comercial del vehículo (Compra Inteligente)."""
    if cuota_balon_pct < 0 or cuota_balon_pct >= 100:
        raise ValueError("La cuota balón debe estar entre 0 % y 99 %.")
    return precio_vehiculo * (cuota_balon_pct / 100.0)


def calcular_cuota_base_metodo_frances(capital_financiado: float, tem: float, n: int) -> float:
    """Cuota fija del método francés (antes de seguros y portes)."""
    if capital_financiado <= 0:
        return 0.0
    if n <= 0:
        raise ValueError("El plazo debe ser mayor a 0.")
    if tem == 0:
        return capital_financiado / n
    return capital_financiado * (tem / (1 - (1 + tem) ** (-n)))


def calcular_cuota_base_con_balon(
    saldo_financiado: float,
    cuota_balon_monto: float,
    tem: float,
    n: int,
) -> float:
    """
    Cuota base con cuota balón al final (valor futuro B).
    C = (S - B/(1+r)^n) * r / (1 - (1+r)^(-n))
    """
    if cuota_balon_monto <= 0:
        return calcular_cuota_base_metodo_frances(saldo_financiado, tem, n)
    if n <= 0:
        raise ValueError("El plazo debe ser mayor a 0.")
    pv_balon = cuota_balon_monto / ((1 + tem) ** n)
    capital_amortizable = saldo_financiado - pv_balon
    if capital_amortizable <= 0:
        raise ValueError("La cuota balón es demasiado alta para el capital financiado.")
    return calcular_cuota_base_metodo_frances(capital_amortizable, tem, n)


def calcular_interes_periodo_k(saldo_inicio_periodo: float, tem: float) -> float:
    return saldo_inicio_periodo * tem


def calcular_amortizacion_periodo_k(cuota_base: float, interes_periodo: float) -> float:
    return cuota_base - interes_periodo


def calcular_capital_vivo_final(saldo_inicio_periodo: float, amortizacion_periodo: float) -> float:
    return max(saldo_inicio_periodo - amortizacion_periodo, 0.0)


def calcular_cuota_total_periodo_k(
    cuota_base: float, seguro_periodo: float, portes: float, cuota_balon: float = 0.0
) -> float:
    return cuota_base + seguro_periodo + portes + cuota_balon


def calcular_van(rate: float, flows: List[float]) -> float:
    total = 0.0
    for idx, f in enumerate(flows):
        total += f / ((1 + rate) ** idx)
    return total


def calcular_tir(flows: List[float], guess: float = 0.01) -> float:
    rate = guess
    for _ in range(200):
        f = 0.0
        df = 0.0
        for idx, cash in enumerate(flows):
            denom = (1 + rate) ** idx
            f += cash / denom
            if idx > 0:
                df -= idx * cash / ((1 + rate) ** (idx + 1))
        if abs(f) < 1e-7:
            return rate
        if abs(df) < 1e-10:
            break
        rate = rate - f / df

    low, high = -0.99, 3.0
    for _ in range(400):
        mid = (low + high) / 2
        f_mid = calcular_van(mid, flows)
        if abs(f_mid) < 1e-7:
            return mid
        f_low = calcular_van(low, flows)
        if f_low * f_mid <= 0:
            high = mid
        else:
            low = mid
    return rate


def calcular_tcea_desde_tir_mensual(tir_mensual: float) -> float:
    return (1 + tir_mensual) ** 12 - 1 if tir_mensual > -1 else math.nan


def _es_compra_inteligente(modalidad: str) -> bool:
    return (modalidad or "").strip().lower() == MODALIDAD_COMPRA_INTELIGENTE.lower()


def build_schedule(
    precio_vehiculo: float,
    cuota_inicial_pct: float,
    tipo_tasa: str,
    tasa_interes: float,
    plazo_meses: int,
    periodo_gracia: str,
    meses_gracia: int,
    seguro_desgravamen: float,
    seguro_vehicular: float,
    portes: float,
    capitalizacion: int | None = None,
    periodo_tasa: int = 7,
    modalidad: str = MODALIDAD_CONVENCIONAL,
    cuota_balon_pct: float = 0.0,
    gastos_notariales: float = 0.0,
    gastos_registrales: float = 0.0,
    costos_iniciales: float = 0.0,
) -> LoanResult:
    if plazo_meses <= 0:
        raise ValueError("El plazo debe ser mayor a 0.")
    if meses_gracia < 0 or meses_gracia >= plazo_meses:
        raise ValueError("Meses de gracia invalidos.")

    modalidad = modalidad or MODALIDAD_CONVENCIONAL
    compra_inteligente = _es_compra_inteligente(modalidad)
    cuota_balon_pct = float(cuota_balon_pct or 0)
    if compra_inteligente:
        if cuota_balon_pct <= 0:
            raise ValueError("En Compra Inteligente indica el porcentaje de cuota balón.")
    else:
        cuota_balon_pct = 0.0

    cuota_inicial_monto = calcular_cuota_inicial_monto(precio_vehiculo, cuota_inicial_pct)
    gastos_iniciales = max(gastos_notariales, 0) + max(gastos_registrales, 0) + max(costos_iniciales, 0)
    saldo = calcular_capital_financiado_total(
        precio_vehiculo,
        cuota_inicial_pct,
        gastos_notariales,
        gastos_registrales,
        costos_iniciales,
    )
    saldo_inicial = saldo

    cuota_balon_monto = 0.0
    if compra_inteligente:
        cuota_balon_monto = calcular_cuota_balon_monto(precio_vehiculo, cuota_balon_pct)
        if cuota_balon_monto >= saldo:
            raise ValueError("La cuota balón debe ser menor al capital financiado total.")

    tem = calcular_tasa_efectiva_mensual(
        tipo_tasa, tasa_interes, capitalizacion, periodo_tasa=periodo_tasa
    )
    gracia = (periodo_gracia or "Ninguno").lower().strip()
    n_regular = plazo_meses - meses_gracia
    if n_regular <= 0:
        raise ValueError("Debe haber al menos un mes regular de pago.")

    capital_amortizable = saldo - cuota_balon_monto / ((1 + tem) ** n_regular) if compra_inteligente else saldo
    if compra_inteligente:
        cuota_base = calcular_cuota_base_con_balon(saldo, cuota_balon_monto, tem, n_regular)
    else:
        cuota_base = calcular_cuota_base_metodo_frances(saldo, tem, n_regular)

    schedule: List[ScheduleRow] = []
    # Perspectiva del deudor: recibe el desembolso (+) y paga cuotas (-)
    flows: List[float] = [saldo_inicial]

    for k in range(1, plazo_meses + 1):
        interes = calcular_interes_periodo_k(saldo, tem)
        seguro = saldo * (seguro_desgravamen + seguro_vehicular)
        amortizacion = 0.0
        balon_pago = 0.0
        cuota = 0.0
        es_ultimo = k == plazo_meses

        if k <= meses_gracia and gracia == "total":
            saldo += interes
            cuota = 0.0
        elif k <= meses_gracia and gracia == "parcial":
            cuota = interes + seguro + portes
        else:
            if compra_inteligente and es_ultimo:
                amortizacion_regular = calcular_amortizacion_periodo_k(cuota_base, interes)
                saldo_tras_cuota = calcular_capital_vivo_final(saldo, amortizacion_regular)
                balon_pago = saldo_tras_cuota
                amortizacion = amortizacion_regular + balon_pago
                saldo = 0.0
                cuota = cuota_base + seguro + portes + balon_pago
            else:
                amortizacion = calcular_amortizacion_periodo_k(cuota_base, interes)
                saldo = calcular_capital_vivo_final(saldo, amortizacion)
                cuota = calcular_cuota_total_periodo_k(cuota_base, seguro, portes, 0.0)

        schedule.append(
            ScheduleRow(
                periodo=k,
                cuota_total=cuota,
                interes=interes,
                amortizacion=amortizacion,
                saldo_final=saldo,
                seguro=seguro,
                portes=portes,
                cuota_balon=balon_pago if compra_inteligente and es_ultimo else 0.0,
            )
        )
        flows.append(-cuota)

    van = calcular_van(tem, flows)
    tir_mensual = calcular_tir(flows)
    tcea = calcular_tcea_desde_tir_mensual(tir_mensual)

    return LoanResult(
        tem=tem,
        cuota_base=cuota_base,
        saldo_inicial=saldo_inicial,
        schedule=schedule,
        flujo=flows,
        van=van,
        tir=tir_mensual,
        tcea=tcea,
        modalidad=modalidad,
        cuota_balon_monto=cuota_balon_monto,
        cuota_inicial_monto=cuota_inicial_monto,
        gastos_iniciales=gastos_iniciales,
        capital_amortizable=capital_amortizable,
    )


to_tem = calcular_tasa_efectiva_mensual
cuota_frances = calcular_cuota_base_metodo_frances
npv = calcular_van
irr = calcular_tir
