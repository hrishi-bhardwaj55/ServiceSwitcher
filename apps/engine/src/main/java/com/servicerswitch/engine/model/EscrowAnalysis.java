package com.servicerswitch.engine.model;

import java.math.BigDecimal;
import java.time.LocalDate;

public record EscrowAnalysis(
    String servicerId,
    LocalDate analysisDate,
    BigDecimal projectedAnnualTax,
    BigDecimal projectedAnnualInsurance,
    BigDecimal currentBalance,
    BigDecimal statedShortage,
    BigDecimal statedMonthlyEscrow,
    BigDecimal statedShortageMonthly,
    BigDecimal newTotalPayment) {}
