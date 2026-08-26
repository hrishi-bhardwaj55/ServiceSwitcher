package com.servicerswitch.engine.model;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

public record MortgageAccount(
        String accountId,
        BigDecimal originalPrincipal,
        BigDecimal currentPrincipal,
        BigDecimal annualRate,
        int termMonths,
        LocalDate originationDate,
        List<ServicingPeriod> servicingPeriods,
        List<Payment> payments,
        List<EscrowTransaction> escrowLedger,
        List<TaxBill> taxBills,
        List<InsurancePolicy> insurancePolicies,
        List<EscrowAnalysis> escrowAnalyses) {}
