-- CREDITOS
SELECT
    credits.id AS id_credito,
    credits.deposit_reference AS referencia_deposito,
    credits.amount AS saldo_inicial,
    credits.annual_interest_rate AS tasa_interes_anual,
    credits.payment_amount AS cuota_mensual,
    credits.operational_opening_date AS fecha_apertura,
    credits.first_payment_date AS fecha_primer_pago
FROM credits
WHERE
    credits.product_id IN (7, 8, 9, 10, 11)
    AND credits.country = 'mx'
ORDER BY credits.id;

-- PAGOS
SELECT
    payments.credit_id AS id_credito,
    payments.amount AS monto_pago,
    payments.date AS fecha_pago
FROM payments
    JOIN credits ON payments.credit_id = credits.id
WHERE
    credits.product_id IN (7, 8, 9, 10, 11)
    AND credits.country = 'mx'
ORDER BY payments.credit_id, payments.date;