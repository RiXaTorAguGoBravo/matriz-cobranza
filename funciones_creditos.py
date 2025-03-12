import numpy as np
import pandas as pd


def pagos_requeridos(creditos: pd.DataFrame, fecha: pd.Timestamp) -> pd.Series:
    """
    Calcula el número de pagos requeridos hasta la fecha especificada.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos. Debe incluir las columnas:
        'fecha_primer_pago', 'plazo' y 'fecha_apertura'.
    fecha : pd.Timestamp
        Fecha de referencia para el cálculo.

    Retorna
    -------
    pd.Series
        Serie con el número de pagos requeridos para cada crédito.
    """
    # Determinar el último día del mes de la fecha dada
    ultimo_dia_mes = fecha + pd.offsets.MonthEnd(0)
    es_ultimo_dia_mes = fecha == ultimo_dia_mes

    # Calcular la diferencia en meses entre la fecha de referencia y la fecha del primer pago
    pagos_req = (
        (fecha.year - creditos['fecha_primer_pago'].dt.year) * 12 +
        (fecha.month - creditos['fecha_primer_pago'].dt.month) -
        ((not es_ultimo_dia_mes) & (fecha.day < creditos['fecha_primer_pago'].dt.day)).astype(int) +
        1
    )

    # Limitar el número de pagos requeridos entre 0 y el plazo del crédito
    pagos_req = pagos_req.clip(lower=0, upper=creditos['plazo']).astype(int)

    # Solo se consideran los créditos cuya fecha de apertura es anterior o igual a la fecha de referencia
    pagos_req = pagos_req.where(creditos['fecha_apertura'] <= fecha)
    return pagos_req


def monto_requerido(creditos: pd.DataFrame, pagos_req: pd.Series) -> pd.Series:
    """
    Calcula el monto total requerido hasta la fecha, basado en la cuota mensual y los pagos requeridos.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos. Debe incluir la columna 'cuota_mensual'.
    pagos_req : pd.Series
        Serie con el número de pagos requeridos para cada crédito.

    Retorna
    -------
    pd.Series
        Serie con el monto requerido para cada crédito.
    """
    return creditos['cuota_mensual'] * pagos_req


def monto_pagado(
    creditos: pd.DataFrame, creditos_pagos: pd.DataFrame, fecha: pd.Timestamp
) -> pd.Series:
    """
    Calcula el monto total pagado hasta la fecha especificada.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos.
    creditos_pagos : pd.DataFrame
        DataFrame con los registros de pagos. Debe incluir 'id_credito', 'fecha_pago' y 'monto_pago'.
    fecha : pd.Timestamp
        Fecha de referencia para el cálculo.

    Retorna
    -------
    pd.Series
        Serie con el monto pagado para cada crédito.
    """
    pagos_filtrados = creditos_pagos[creditos_pagos['fecha_pago'] <= fecha]
    monto_pag = pagos_filtrados.groupby('id_credito')['monto_pago'].sum()
    monto_pag = monto_pag.reindex(creditos.index)

    # Para créditos sin pagos (o que aún no han iniciado) se asigna 0
    monto_pag = monto_pag.where((fecha < creditos['fecha_apertura']) | monto_pag.notnull(), 0)
    return monto_pag


def estatus(monto_req: pd.Series, monto_pag: pd.Series) -> pd.Series:
    """
    Determina el estatus de cada crédito basado en el monto requerido y el monto pagado.

    Parámetros
    ----------
    monto_req : pd.Series
        Serie con el monto requerido hasta la fecha.
    monto_pag : pd.Series
        Serie con el monto pagado hasta la fecha.

    Retorna
    -------
    pd.Series
        Serie con el estatus de cada crédito:
        - 'Atrasado' si el pago es inferior al 98% del requerido.
        - 'Al Corriente' si el pago se encuentra entre el 98% y el 100% del requerido.
        - 'Adelantado' si el pago excede el monto requerido.
    """
    est = pd.Series(pd.NA, index=monto_req.index, name='estatus')
    est[monto_pag < monto_req * 0.98] = 'Atrasado'
    est[(monto_req * 0.98 <= monto_pag) & (monto_pag <= monto_req)] = 'Al Corriente'
    est[monto_pag > monto_req] = 'Adelantado'
    return est


def fecha_ultimo_pago(
    creditos: pd.DataFrame, creditos_pagos: pd.DataFrame, fecha: pd.Timestamp
) -> pd.Series:
    """
    Obtiene la fecha del último pago realizado hasta la fecha especificada.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos.
    creditos_pagos : pd.DataFrame
        DataFrame con los registros de pagos. Debe incluir 'id_credito' y 'fecha_pago'.
    fecha : pd.Timestamp
        Fecha de referencia para el cálculo.

    Retorna
    -------
    pd.Series
        Serie con la fecha del último pago para cada crédito.
    """
    ult_pago = creditos_pagos[creditos_pagos['fecha_pago'] <= fecha] \
        .groupby('id_credito')['fecha_pago'].last()
    ult_pago = ult_pago.reindex(creditos.index)
    return ult_pago


def dias_sin_pagar(
    creditos: pd.DataFrame, fecha_ult_pago: pd.Series, fecha: pd.Timestamp
) -> pd.Series:
    """
    Calcula el número de días sin realizar pagos, descontando un período de 30 días.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos. Debe incluir 'fecha_apertura'.
    fecha_ult_pago : pd.Series
        Serie con la fecha del último pago para cada crédito.
    fecha : pd.Timestamp
        Fecha de referencia para el cálculo.

    Retorna
    -------
    pd.Series
        Serie con los días sin pagar para cada crédito.
    """
    dias = ((fecha - fecha_ult_pago).dt.days - 30).clip(lower=0)
    # En caso de que no exista fecha de último pago y el crédito ya inició, se calcula desde la fecha de apertura
    dias = (fecha - creditos['fecha_apertura']).dt.days.astype(float).where(
        dias.isnull() & (creditos['fecha_apertura'] <= fecha), dias
    )
    return dias


def atraso_pagos(
    creditos: pd.DataFrame, pagos_req: pd.Series, monto_pag: pd.Series
) -> pd.Series:
    """
    Calcula el atraso en pagos en función de los pagos requeridos y el monto pagado.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos. Debe incluir 'cuota_mensual'.
    pagos_req : pd.Series
        Serie con el número de pagos requeridos hasta la fecha.
    monto_pag : pd.Series
        Serie con el monto pagado hasta la fecha.

    Retorna
    -------
    pd.Series
        Serie con el número de pagos en atraso para cada crédito.
    """
    pagos_realizados = np.round(monto_pag / creditos['cuota_mensual'] + 1e-10, 0)
    return pagos_req - pagos_realizados


def logica_paridad(row: pd.Series, fecha: pd.Timestamp) -> str:
    """
    Determina el tipo de paridad de un crédito basado en su estatus, días sin pagar y atraso en pagos.

    Parámetros
    ----------
    row : pd.Series
        Fila de un DataFrame que debe incluir las columnas:
        'fecha_apertura', 'estatus', 'dias_sin_pagar' y 'atraso_pagos'.
    fecha : pd.Timestamp
        Fecha de referencia para el cálculo.

    Retorna
    -------
    str
        Tipo de paridad (por ejemplo, 'Al Corriente', 'PAR 30', etc.).
    """
    if fecha < row['fecha_apertura']:
        return 'Al Corriente'
    if row['atraso_pagos'] <= 0:
        if row['estatus'] != "Atrasado":
            return "Al Corriente"
        if row['dias_sin_pagar'] > 360:
            return "PAR 360"
        if row['dias_sin_pagar'] > 270:
            return "PAR 270"
        if row['dias_sin_pagar'] > 180:
            return "PAR 180"
        if row['dias_sin_pagar'] > 150:
            return "PAR 150"
        if row['dias_sin_pagar'] > 120:
            return "PAR 120"
        if row['dias_sin_pagar'] > 90:
            return "PAR 90"
        if row['dias_sin_pagar'] > 60:
            return "PAR 60"
        if row['dias_sin_pagar'] > 30:
            return "PAR 30"
        return "PAR 1"

    if row['dias_sin_pagar'] > 360 or row['atraso_pagos'] >= 13:
        return "PAR 360"
    if row['dias_sin_pagar'] > 270 or row['atraso_pagos'] >= 10:
        return "PAR 270"
    if row['dias_sin_pagar'] > 180 or row['atraso_pagos'] >= 7:
        return "PAR 180"
    if row['dias_sin_pagar'] > 150 or row['atraso_pagos'] >= 6:
        return "PAR 150"
    if row['dias_sin_pagar'] > 120 or row['atraso_pagos'] >= 5:
        return "PAR 120"
    if row['dias_sin_pagar'] > 90 or row['atraso_pagos'] >= 4:
        return "PAR 90"
    if row['dias_sin_pagar'] > 60 or row['atraso_pagos'] >= 3:
        return "PAR 60"
    if row['dias_sin_pagar'] > 30 or row['atraso_pagos'] >= 2:
        return "PAR 30"
    return "PAR 1"


def tipo_paridad(
    creditos: pd.DataFrame,
    estatus_series: pd.Series,
    dias_sin_pagar_series: pd.Series,
    atraso_series: pd.Series,
    fecha: pd.Timestamp
) -> pd.Series:
    """
    Asigna el tipo de paridad a cada crédito aplicando la lógica de paridad.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos. Debe incluir 'fecha_apertura'.
    estatus_series : pd.Series
        Serie con el estatus ('Atrasado', 'Al Corriente', etc.) de cada crédito.
    dias_sin_pagar_series : pd.Series
        Serie con los días sin pagar para cada crédito.
    atraso_series : pd.Series
        Serie con el número de pagos en atraso para cada crédito.
    fecha : pd.Timestamp
        Fecha de referencia para el cálculo.

    Retorna
    -------
    pd.Series
        Serie con el tipo de paridad asignado a cada crédito.
    """
    df = pd.DataFrame({
        'fecha_apertura': creditos['fecha_apertura'],
        'estatus': estatus_series,
        'dias_sin_pagar': dias_sin_pagar_series,
        'atraso_pagos': atraso_series
    })
    return df.apply(lambda row: logica_paridad(row, fecha), axis=1)


def paridad(
    creditos: pd.DataFrame, creditos_pagos: pd.DataFrame, fecha: pd.Timestamp
) -> pd.Series:
    """
    Calcula la paridad de cada crédito basándose en los indicadores de pagos.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos.
    creditos_pagos : pd.DataFrame
        DataFrame con los registros de pagos.
    fecha : pd.Timestamp
        Fecha de referencia para el cálculo.

    Retorna
    -------
    pd.Series
        Serie con el tipo de paridad asignado a cada crédito.
    """
    pagos_req = pagos_requeridos(creditos, fecha)
    monto_req = monto_requerido(creditos, pagos_req)
    monto_pag = monto_pagado(creditos, creditos_pagos, fecha)
    estatus_series = estatus(monto_req, monto_pag)
    fecha_ult_pago = fecha_ultimo_pago(creditos, creditos_pagos, fecha)
    dias_sin_pago = dias_sin_pagar(creditos, fecha_ult_pago, fecha)
    atraso_series = atraso_pagos(creditos, pagos_req, monto_pag)
    return tipo_paridad(creditos, estatus_series, dias_sin_pago, atraso_series, fecha)


def paridad_inicial(
    creditos: pd.DataFrame, creditos_pagos: pd.DataFrame, fecha: pd.Timestamp
) -> pd.Series:
    """
    Calcula la paridad inicial de cada crédito utilizando la fecha anterior
    al inicio del mes de referencia.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos.
    creditos_pagos : pd.DataFrame
        DataFrame con los registros de pagos.
    fecha : pd.Timestamp
        Fecha de referencia para el cálculo.

    Retorna
    -------
    pd.Series
        Serie con el tipo de paridad inicial asignado a cada crédito.
    """
    # Ajustar la fecha: se toma el inicio del mes y se resta un día
    fecha_ajustada = fecha.to_period('M').start_time - pd.Timedelta(days=1)
    return paridad(creditos, creditos_pagos, fecha_ajustada)


def saldo(
    creditos: pd.DataFrame, creditos_pagos: pd.DataFrame, fecha: pd.Timestamp
) -> pd.Series:
    """
    Obtiene el saldo posterior a los pagos realizados hasta la fecha especificada.
    Si no hay registros de pago, utiliza el saldo inicial del crédito.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos. Debe incluir 'saldo_inicial'.
    creditos_pagos : pd.DataFrame
        DataFrame con los registros de pagos. Debe incluir:
        'id_credito', 'fecha_pago' y 'saldo_posterior'.
    fecha : pd.Timestamp
        Fecha de referencia para el cálculo.

    Retorna
    -------
    pd.Series
        Serie con el saldo correspondiente para cada crédito.
    """
    pagos_filtrados = creditos_pagos[creditos_pagos['fecha_pago'] <= fecha]
    saldo_series = pagos_filtrados.groupby('id_credito')['saldo_posterior'].last()
    saldo_series = saldo_series.reindex(creditos.index)
    saldo_series = saldo_series.where(saldo_series.notnull(), creditos['saldo_inicial'])
    return saldo_series


def saldo_inicial(
    creditos: pd.DataFrame, creditos_pagos: pd.DataFrame, fecha: pd.Timestamp
) -> pd.Series:
    """
    Calcula el saldo inicial de cada crédito utilizando la fecha anterior al inicio
    del mes de referencia.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos.
    creditos_pagos : pd.DataFrame
        DataFrame con los registros de pagos.
    fecha : pd.Timestamp
        Fecha de referencia para el cálculo.

    Retorna
    -------
    pd.Series
        Serie con el saldo inicial para cada crédito.
    """
    fecha_ajustada = fecha.to_period('M').start_time - pd.Timedelta(days=1)
    return saldo(creditos, creditos_pagos, fecha_ajustada)


def considerar(creditos: pd.DataFrame, fecha: pd.Timestamp) -> pd.DataFrame:
    """
    Determina qué créditos deben ser considerados basado en su fecha de apertura y cierre.

    Parámetros
    ----------
    creditos : pd.DataFrame
        DataFrame con la información de los créditos. Debe incluir:
        'fecha_apertura' y 'fecha_cierre'.
    fecha : pd.Timestamp
        Fecha de referencia para el cálculo.

    Retorna
    -------
    pd.DataFrame
        Subconjunto del DataFrame original que contiene solo los créditos que deben ser considerados.
    """
    fecha_actual = fecha.to_period('M').start_time
    fecha_maxima = pd.Timestamp('2200-12-31')

    # Fecha inicial: el inicio del mes siguiente a la apertura del crédito
    fecha_inicial = (creditos['fecha_apertura'].dt.to_period('M') + 1).dt.start_time

    # Fecha final: se usa la fecha de cierre, o una fecha muy lejana si no tiene cierre
    fecha_final = creditos['fecha_cierre'].fillna(fecha_maxima)

    # Filtra y retorna un subconjunto del DataFrame con los créditos considerados
    return creditos[(fecha_inicial <= fecha_actual) & (fecha_actual < fecha_final)].copy()