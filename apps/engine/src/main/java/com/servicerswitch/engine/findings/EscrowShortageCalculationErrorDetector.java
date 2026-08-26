package com.servicerswitch.engine.findings;

import static com.servicerswitch.engine.findings.FindingSupport.finding;
import static com.servicerswitch.engine.money.Money.TWELVE;
import static com.servicerswitch.engine.money.Money.absoluteDifference;
import static com.servicerswitch.engine.money.Money.divide;

import com.servicerswitch.engine.model.EscrowAnalysis;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

public final class EscrowShortageCalculationErrorDetector implements FindingDetector {
  @Override
  public Optional<Finding> detect(ReconciliationContext context) {
    EscrowAnalysis analysis =
        context.account().escrowAnalyses().get(context.account().escrowAnalyses().size() - 1);
    BigDecimal expected = context.escrowComputation().shortage();
    BigDecimal difference = absoluteDifference(expected, analysis.statedShortage());
    if (difference.compareTo(Tolerances.SHORTAGE) <= 0) {
      return Optional.empty();
    }
    return Optional.of(
        finding(
            FindingType.ESCROW_SHORTAGE_CALCULATION_ERROR,
            expected,
            analysis.statedShortage(),
            difference,
            divide(difference, TWELVE),
            "The stated shortage does not match the aggregate trial-balance calculation.",
            List.of(
                new Evidence(
                    "doc_escrow_analysis", 1, "stated_shortage", analysis.statedShortage())),
            "Ask the servicer for the escrow trial balance and shortage calculation."));
  }
}
