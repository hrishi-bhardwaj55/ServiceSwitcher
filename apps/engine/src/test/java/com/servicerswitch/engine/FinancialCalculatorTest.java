package com.servicerswitch.engine;

import static com.servicerswitch.engine.TestAccounts.amount;
import static org.assertj.core.api.Assertions.assertThat;

import com.servicerswitch.engine.escrow.EscrowCalculator;
import com.servicerswitch.engine.escrow.EscrowComputation;
import com.servicerswitch.engine.findings.FindingType;
import com.servicerswitch.engine.model.EscrowAnalysis;
import com.servicerswitch.engine.model.InsurancePolicy;
import com.servicerswitch.engine.model.MortgageAccount;
import com.servicerswitch.engine.model.Payment;
import com.servicerswitch.engine.model.TaxBill;
import com.servicerswitch.engine.payment.PaymentCalculator;
import com.servicerswitch.engine.payment.PaymentDecomposition;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;

class FinancialCalculatorTest {
    @Test
    void recomputesWorkedEscrowShortageExample() {
        MortgageAccount base = TestAccounts.baseAccount();
        EscrowAnalysis analysis = new EscrowAnalysis(
                "NEW",
                LocalDate.of(2025, 1, 1),
                amount("4800.00"),
                amount("1200.00"),
                amount("1200.00"),
                amount("400.00"),
                amount("500.00"),
                amount("33.33"),
                amount("2043.43"));
        MortgageAccount account = new MortgageAccount(
                base.accountId(), base.originalPrincipal(), base.currentPrincipal(), base.annualRate(),
                base.termMonths(), base.originationDate(), base.servicingPeriods(), base.payments(),
                base.escrowLedger(),
                List.of(new TaxBill("County", 2025, amount("4800.00"),
                        List.of(LocalDate.of(2025, 6, 15), LocalDate.of(2025, 12, 15)))),
                List.of(new InsurancePolicy("Beacon", amount("1200.00"), LocalDate.of(2025, 3, 20))),
                List.of(analysis));

        EscrowComputation result = new EscrowCalculator().compute(account, analysis, 2025);

        assertThat(result.monthlyEscrow()).isEqualByComparingTo("500.00");
        assertThat(result.lowBalance()).isEqualByComparingTo("600.00");
        assertThat(result.cushion()).isEqualByComparingTo("1000.00");
        assertThat(result.shortage()).isEqualByComparingTo("400.00");
        assertThat(result.shortageMonthly()).isEqualByComparingTo("33.33");
    }

    @Test
    void emitsExactExplainedPaymentDecomposition() {
        MortgageAccount base = TestAccounts.baseAccount();
        EscrowAnalysis oldAnalysis = TestAccounts.analysis(
                LocalDate.of(2024, 5, 31), amount("1200.00"), amount("6000.00"), amount("0.00"));
        EscrowAnalysis newAnalysis = new EscrowAnalysis(
                "NEW", TestAccounts.TRANSFER_DATE, amount("9000.00"), amount("1440.00"),
                amount("1200.00"), amount("480.00"), amount("870.00"), amount("40.00"), amount("2360.00"));
        MortgageAccount account = new MortgageAccount(
                base.accountId(), base.originalPrincipal(), base.currentPrincipal(), base.annualRate(),
                base.termMonths(), base.originationDate(), base.servicingPeriods(),
                List.of(
                        new Payment(LocalDate.of(2024, 5, 1), amount("2050.00"), amount("100.00"), amount("1350.00"), amount("600.00")),
                        new Payment(TestAccounts.TRANSFER_DATE, amount("2360.00"), amount("101.00"), amount("1349.00"), amount("910.00"))),
                base.escrowLedger(), base.taxBills(), base.insurancePolicies(),
                List.of(oldAnalysis, newAnalysis));

        PaymentDecomposition result = new PaymentCalculator().decompose(
                account, TestAccounts.TRANSFER_DATE);

        assertThat(result.paymentChange()).isEqualByComparingTo("310.00");
        assertThat(result.taxChangeMonthly()).isEqualByComparingTo("250.00");
        assertThat(result.insuranceChangeMonthly()).isEqualByComparingTo("20.00");
        assertThat(result.shortageMonthly()).isEqualByComparingTo("40.00");
        assertThat(result.residual()).isEqualByComparingTo("0.00");
        assertThat(result.outcome()).isEqualTo(FindingType.EXPLAINED);
    }
}
