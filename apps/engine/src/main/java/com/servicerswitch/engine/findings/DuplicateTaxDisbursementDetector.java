package com.servicerswitch.engine.findings;

import static com.servicerswitch.engine.findings.FindingSupport.finding;
import static com.servicerswitch.engine.money.Money.ZERO;
import static com.servicerswitch.engine.money.Money.cents;

import com.servicerswitch.engine.model.EscrowTransaction;
import com.servicerswitch.engine.model.TransactionType;
import java.math.BigDecimal;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;

public final class DuplicateTaxDisbursementDetector implements FindingDetector {
  @Override
  public Optional<Finding> detect(ReconciliationContext context) {
    List<EscrowTransaction> taxes =
        context.account().escrowLedger().stream()
            .filter(transaction -> transaction.type() == TransactionType.TAX_DISBURSEMENT)
            .toList();
    for (int firstIndex = 0; firstIndex < taxes.size(); firstIndex++) {
      for (int secondIndex = firstIndex + 1; secondIndex < taxes.size(); secondIndex++) {
        EscrowTransaction first = taxes.get(firstIndex);
        EscrowTransaction second = taxes.get(secondIndex);
        long days = Math.abs(ChronoUnit.DAYS.between(first.date(), second.date()));
        BigDecimal larger = first.amount().abs().max(second.amount().abs());
        BigDecimal amountDifference = first.amount().abs().subtract(second.amount().abs()).abs();
        if (first.payee().equals(second.payee())
            && days <= Tolerances.DUPLICATE_DAYS
            && amountDifference.compareTo(larger.multiply(Tolerances.DUPLICATE_PERCENT)) <= 0) {
          BigDecimal impact = cents(second.amount().abs());
          return Optional.of(
              finding(
                  FindingType.DUPLICATE_TAX_DISBURSEMENT,
                  impact,
                  impact,
                  impact,
                  ZERO,
                  "Two similar tax disbursements to the same payee occurred within 45 days.",
                  List.of(
                      new Evidence("doc_new_servicer_statement", 1, "tax_disbursement", impact)),
                  "Ask the servicer to identify the obligation supported by each payment."));
        }
      }
    }
    return Optional.empty();
  }
}
