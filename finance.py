from __future__ import annotations

from dataclasses import dataclass
import math
from typing import List


@dataclass
class ScheduleRow:
    periodo: int
    cuota_total: float
    interes: float
    amortizacion: float
    saldo_final: float
    seguro: float
    portes: float


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


def calcular_tasa_efectiva_mensual(
    tipo_tasa: str, tasa: float, capitalizacion: int | None = None
) -> float:
    """
    Cap. 4.1: Conversion de tasa (efectiva/nominal) a TEM.
    tasa se espera en decimal (ej. 0.125 para 12.5%).
    """
    if tasa <= 0:
        raise ValueError("La tasa debe ser mayor a 0.")

    tipo = tipo_tasa.lower().strip()
    if tipo == "efectiva":
        tea = tasa
    elif tipo == "nominal":
        c = capitalizacion or 12
        if c <= 0:
            raise ValueError("La capitalizacion debe ser mayor a 0.")
        tea = (1 + tasa / c) ** c - 1
    else:
        raise ValueError("tipo_tasa debe ser 'Efectiva' o 'Nominal'.")

    return (1 + tea) ** (1 / 12) - 1


def calcular_capital_financiado(precio_vehiculo: float, cuota_inicial_pct: float) -> float:
    """
    Cap. 4.2: Capital financiado.
    """
    if precio_vehiculo <= 0:
        raise ValueError("El precio del vehiculo debe ser mayor a 0.")
    if not (0 <= cuota_inicial_pct < 100):
        raise ValueError("La cuota inicial debe estar entre 0 y 100.")

    cuota_inicial = precio_vehiculo * (cuota_inicial_pct / 100.0)
    return precio_vehiculo - cuota_inicial


def calcular_cuota_base_metodo_frances(capital_financiado: float, tem: float, n: int) -> float:
    """
    Cap. 4.3: Cuota base del metodo frances.
    """
    if n <= 0:
        raise ValueError("El plazo debe ser mayor a 0.")
    if tem == 0:
        return capital_financiado / n
    return capital_financiado * (tem / (1 - (1 + tem) ** (-n)))


def calcular_interes_periodo_k(saldo_inicio_periodo: float, tem: float) -> float:
    """
    Cap. 4.4: Interes del periodo k.
    """
    return saldo_inicio_periodo * tem


def calcular_amortizacion_periodo_k(cuota_base: float, interes_periodo: float) -> float:
    """
    Cap. 4.5: Amortizacion del periodo k.
    """
    return cuota_base - interes_periodo


def calcular_capital_vivo_final(saldo_inicio_periodo: float, amortizacion_periodo: float) -> float:
    """
    Cap. 4.6: Capital vivo al final del periodo k.
    """
    return max(saldo_inicio_periodo - amortizacion_periodo, 0.0)


def calcular_cuota_total_periodo_k(
    cuota_base: float, seguro_periodo: float, portes: float
) -> float:
    """
    Cap. 4.7: Cuota total del periodo k.
    """
    return cuota_base + seguro_periodo + portes


def calcular_van(rate: float, flows: List[float]) -> float:
    """
    Cap. 4.8: VAN.
    """
    total = 0.0
    for idx, f in enumerate(flows):
        total += f / ((1 + rate) ** idx)
    return total


def calcular_tir(flows: List[float], guess: float = 0.01) -> float:
    """
    Cap. 4.9: TIR (mensual), via Newton-Raphson + biseccion.
    """
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
    """
    Cap. 4.10: TCEA desde tasa mensual equivalente.
    """
    return (1 + tir_mensual) ** 12 - 1 if tir_mensual > -1 else math.nan


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
) -> LoanResult:
    if plazo_meses <= 0:
        raise ValueError("El plazo debe ser mayor a 0.")
    if meses_gracia < 0 or meses_gracia > plazo_meses:
        raise ValueError("Meses de gracia invalidos.")

    # 4.2 Capital financiado
    saldo = calcular_capital_financiado(precio_vehiculo, cuota_inicial_pct)
    saldo_inicial = saldo

    # 4.1 Conversion a TEM
    tem = calcular_tasa_efectiva_mensual(tipo_tasa, tasa_interes, capitalizacion)
    gracia = (periodo_gracia or "Ninguno").lower().strip()
    n_regular = plazo_meses - meses_gracia
    # 4.3 Cuota base
    cuota_base = calcular_cuota_base_metodo_frances(saldo, tem, n_regular if n_regular > 0 else 1)

    schedule: List[ScheduleRow] = []
    flows: List[float] = [-saldo_inicial]

    for k in range(1, plazo_meses + 1):
        # 4.4 Interes del periodo k
        interes = calcular_interes_periodo_k(saldo, tem)
        seguro = saldo * (seguro_desgravamen + seguro_vehicular)
        amortizacion = 0.0
        cuota = 0.0

        if k <= meses_gracia and gracia == "total":
            saldo += interes
            cuota = 0.0
        elif k <= meses_gracia and gracia == "parcial":
            cuota = interes + seguro + portes
        else:
            # 4.5 Amortizacion
            amortizacion = calcular_amortizacion_periodo_k(cuota_base, interes)
            # 4.6 Capital vivo final
            saldo = calcular_capital_vivo_final(saldo, amortizacion)
            # 4.7 Cuota total
            cuota = calcular_cuota_total_periodo_k(cuota_base, seguro, portes)

        schedule.append(
            ScheduleRow(
                periodo=k,
                cuota_total=cuota,
                interes=interes,
                amortizacion=amortizacion,
                saldo_final=saldo,
                seguro=seguro,
                portes=portes,
            )
        )
        flows.append(cuota)

    # 4.8 VAN, 4.9 TIR, 4.10 TCEA
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
    )


# Alias para compatibilidad con versiones previas
to_tem = calcular_tasa_efectiva_mensual
cuota_frances = calcular_cuota_base_metodo_frances
npv = calcular_van
irr = calcular_tir
