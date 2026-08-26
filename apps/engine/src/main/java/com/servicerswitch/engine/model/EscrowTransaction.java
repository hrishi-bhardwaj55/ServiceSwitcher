package com.servicerswitch.engine.model;

import java.math.BigDecimal;
import java.time.LocalDate;

public record EscrowTransaction(
    LocalDate date,
    TransactionType type,
    BigDecimal amount,
    String payee,
    BigDecimal balanceAfter) {}
