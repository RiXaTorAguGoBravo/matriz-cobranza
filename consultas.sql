SELECT
    credits.id AS id_credito,
    credits.deposit_reference AS referencia_deposito,
    credits.amount AS saldo_inicial,
    credits.annual_interest_rate AS tasa_interes_anual,
    credits.payment_amount AS cuota_mensual,
    credits.term AS plazo,
    credits.operational_opening_date AS fecha_apertura,
    credits.first_payment_date AS fecha_primer_pago,
    CASE 
        WHEN NOT credits.open THEN LEAST(
            (SELECT MAX(payments_2.date) FROM payments AS payments_2 WHERE payments_2.credit_id = credits.id),
            credits.closing_date
        )
        ELSE NULL
    END AS fecha_cierre, -- CONSIDERAMOS QUE LA FECHA DE CIERRE CORRESPONDE A LA FECHA DEL ULTIMO PAGO REALIZADO
    payments.date AS fecha_pago,
    payments.amount AS monto_pago
FROM credits
    LEFT JOIN payments ON credits.id = payments.credit_id
WHERE
    credits.country = 'mx'
    AND credits.product_id IN (7, 8, 9, 10, 11)
ORDER BY credits.id, payments.date;