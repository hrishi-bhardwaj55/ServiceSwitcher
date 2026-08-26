package com.servicerswitch.engine.escrow;

import java.math.BigDecimal;

public record EscrowComputation(
        BigDecimal monthlyEscrow,
        BigDecimal lowBalance,
        BigDecimal cushion,
        BigDecimal shortage,
        BigDecimal shortageMonthly) {}
