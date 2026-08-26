package com.servicerswitch.engine.model;

import java.math.BigDecimal;
import java.time.LocalDate;

public record InsurancePolicy(
        String carrier,
        BigDecimal annualPremium,
        LocalDate renewalDate) {}
