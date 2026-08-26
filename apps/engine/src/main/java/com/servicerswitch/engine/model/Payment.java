package com.servicerswitch.engine.model;

import java.math.BigDecimal;
import java.time.LocalDate;

public record Payment(
    LocalDate date,
    BigDecimal total,
    BigDecimal principal,
    BigDecimal interest,
    BigDecimal escrow) {}
