package com.servicerswitch.engine;

import com.servicerswitch.engine.escrow.EscrowComputation;
import com.servicerswitch.engine.findings.FindingType;
import com.servicerswitch.engine.findings.ReconciliationContext;
import com.servicerswitch.engine.model.EscrowAnalysis;
import com.servicerswitch.engine.model.EscrowTransaction;
import com.servicerswitch.engine.model.InsurancePolicy;
import com.servicerswitch.engine.model.MortgageAccount;
import com.servicerswitch.engine.model.Payment;
import com.servicerswitch.engine.model.ServicingPeriod;
import com.servicerswitch.engine.model.TaxBill;
import com.servicerswitch.engine.payment.PaymentDecomposition;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

public final class TestAccounts {
    public static final LocalDate TRANSFER_DATE = LocalDate.of(2024, 6, 1);

    private TestAccounts() {}

    public static BigDecimal amount(String value) {
        return new BigDecimal(value);
    }

    public static EscrowAnalysis analysis(
            LocalDate date,
            BigDecimal balance,
            BigDecimal projectedTax,
            BigDecimal shortage) {
        BigDecimal shortageMonthly = shortage.divide(
                new BigDecimal("12"), 2, java.math.RoundingMode.HALF_UP);
        return new EscrowAnalysis(
                date.isBefore(TRANSFER_DATE) ? "OLD" : "NEW",
                date,
                projectedTax,
                amount("1200.00"),
                balance,
                shortage,
                amount("600.00"),
                shortageMonthly,
                amount("2050.00").add(shortageMonthly));
    }

    public static MortgageAccount account(
            EscrowAnalysis oldAnalysis,
            EscrowAnalysis newAnalysis,
            List<EscrowTransaction> ledger) {
        return new MortgageAccount(
                "SS-TEST",
                amount("300000.00"),
                amount("290000.00"),
                amount("0.0600"),
                360,
                LocalDate.of(2024, 1, 1),
                List.of(
                        new ServicingPeriod("OLD", LocalDate.of(2024, 1, 1), LocalDate.of(2024, 5, 31)),
                        new ServicingPeriod("NEW", TRANSFER_DATE, null)),
                List.of(
                        new Payment(LocalDate.of(2024, 5, 1), amount("2050.00"), amount("100.00"), amount("1350.00"), amount("600.00")),
                        new Payment(TRANSFER_DATE, amount("2050.00"), amount("101.00"), amount("1349.00"), amount("600.00"))),
                ledger,
                List.of(
                        new TaxBill("County", 2024, amount("6000.00"), List.of(LocalDate.of(2024, 6, 15), LocalDate.of(2024, 12, 15))),
                        new TaxBill("County", 2025, amount("6000.00"), List.of(LocalDate.of(2025, 6, 15), LocalDate.of(2025, 12, 15)))),
                List.of(
                        new InsurancePolicy("Beacon", amount("1200.00"), LocalDate.of(2024, 3, 20)),
                        new InsurancePolicy("Beacon", amount("1200.00"), LocalDate.of(2025, 3, 20))),
                List.of(
                        analysis(LocalDate.of(2024, 1, 1), amount("1200.00"), amount("6000.00"), amount("400.00")),
                        oldAnalysis,
                        newAnalysis));
    }

    public static MortgageAccount baseAccount() {
        return account(
                analysis(LocalDate.of(2024, 5, 31), amount("1200.00"), amount("6000.00"), amount("400.00")),
                analysis(TRANSFER_DATE, amount("1200.00"), amount("6000.00"), amount("400.00")),
                List.of());
    }

    public static ReconciliationContext context(MortgageAccount account) {
        return context(account, amount("400.00"), explainedDecomposition());
    }

    public static ReconciliationContext context(
            MortgageAccount account,
            BigDecimal expectedShortage,
            PaymentDecomposition decomposition) {
        return new ReconciliationContext(
                account,
                TRANSFER_DATE,
                new EscrowComputation(
                        amount("600.00"),
                        amount("800.00"),
                        amount("1200.00"),
                        expectedShortage,
                        expectedShortage.divide(new BigDecimal("12"), 2, java.math.RoundingMode.HALF_UP)),
                decomposition);
    }

    public static PaymentDecomposition explainedDecomposition() {
        return decomposition(amount("10.00"), amount("10.00"), FindingType.EXPLAINED);
    }

    public static PaymentDecomposition decomposition(
            BigDecimal residual, BigDecimal tolerance, FindingType outcome) {
        return new PaymentDecomposition(
                amount("310.00"),
                amount("0.00"),
                amount("250.00"),
                amount("20.00"),
                amount("40.00"),
                residual,
                tolerance,
                outcome);
    }
}
