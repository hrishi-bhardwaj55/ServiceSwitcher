package com.servicerswitch.engine.model;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

public record TaxBill(
        String authority,
        int taxYear,
        BigDecimal annualAmount,
        List<LocalDate> dueDates) {}
