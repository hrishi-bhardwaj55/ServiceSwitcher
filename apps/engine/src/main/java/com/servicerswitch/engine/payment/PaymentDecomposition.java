package com.servicerswitch.engine.payment;

import com.servicerswitch.engine.findings.FindingType;
import java.math.BigDecimal;

public record PaymentDecomposition(
    BigDecimal paymentChange,
    BigDecimal principalInterestChange,
    BigDecimal taxChangeMonthly,
    BigDecimal insuranceChangeMonthly,
    BigDecimal shortageMonthly,
    BigDecimal residual,
    BigDecimal tolerance,
    FindingType outcome) {}
