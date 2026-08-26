package com.servicerswitch.engine.payment;

import static com.servicerswitch.engine.money.Money.TWELVE;
import static com.servicerswitch.engine.money.Money.cents;
import static com.servicerswitch.engine.money.Money.divide;
import static com.servicerswitch.engine.money.Money.maximum;

import com.servicerswitch.engine.findings.FindingType;
import com.servicerswitch.engine.findings.Tolerances;
import com.servicerswitch.engine.model.EscrowAnalysis;
import com.servicerswitch.engine.model.MortgageAccount;
import com.servicerswitch.engine.model.Payment;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Comparator;

public final class PaymentCalculator {
  public PaymentDecomposition decompose(MortgageAccount account, LocalDate transferDate) {
    Payment oldPayment =
        account.payments().stream()
            .filter(payment -> payment.date().isBefore(transferDate))
            .max(Comparator.comparing(Payment::date))
            .orElseThrow(() -> new IllegalArgumentException("missing pre-transfer payment"));
    Payment newPayment =
        account.payments().stream()
            .filter(payment -> !payment.date().isBefore(transferDate))
            .min(Comparator.comparing(Payment::date))
            .orElseThrow(() -> new IllegalArgumentException("missing post-transfer payment"));
    int size = account.escrowAnalyses().size();
    EscrowAnalysis oldAnalysis = account.escrowAnalyses().get(size - 2);
    EscrowAnalysis newAnalysis = account.escrowAnalyses().get(size - 1);
    BigDecimal paymentChange = cents(newPayment.total().subtract(oldPayment.total()));
    BigDecimal principalInterestChange =
        cents(
            newPayment
                .principal()
                .add(newPayment.interest())
                .subtract(oldPayment.principal().add(oldPayment.interest())));
    BigDecimal taxChange =
        divide(newAnalysis.projectedAnnualTax().subtract(oldAnalysis.projectedAnnualTax()), TWELVE);
    BigDecimal insuranceChange =
        divide(
            newAnalysis.projectedAnnualInsurance().subtract(oldAnalysis.projectedAnnualInsurance()),
            TWELVE);
    BigDecimal residual =
        cents(
            paymentChange
                .subtract(principalInterestChange)
                .subtract(taxChange)
                .subtract(insuranceChange)
                .subtract(newAnalysis.statedShortageMonthly()));
    BigDecimal tolerance =
        maximum(
            Tolerances.PAYMENT_ABSOLUTE, cents(paymentChange.multiply(Tolerances.PAYMENT_PERCENT)));
    FindingType outcome =
        residual.compareTo(tolerance) > 0
            ? FindingType.UNEXPLAINED_PAYMENT_INCREASE
            : FindingType.EXPLAINED;
    return new PaymentDecomposition(
        paymentChange,
        principalInterestChange,
        taxChange,
        insuranceChange,
        newAnalysis.statedShortageMonthly(),
        residual,
        tolerance,
        outcome);
  }
}
