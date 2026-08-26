package com.servicerswitch.engine.findings;

import static com.servicerswitch.engine.findings.FindingSupport.finding;
import static com.servicerswitch.engine.money.Money.ZERO;
import static com.servicerswitch.engine.money.Money.absoluteDifference;

import com.servicerswitch.engine.model.EscrowAnalysis;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

public final class EscrowBalanceMismatchDetector implements FindingDetector {
    @Override
    public Optional<Finding> detect(ReconciliationContext context) {
        List<EscrowAnalysis> analyses = context.account().escrowAnalyses();
        EscrowAnalysis oldAnalysis = analyses.get(analyses.size() - 2);
        EscrowAnalysis newAnalysis = analyses.get(analyses.size() - 1);
        BigDecimal difference = absoluteDifference(
                oldAnalysis.currentBalance(), newAnalysis.currentBalance());
        if (difference.compareTo(Tolerances.ESCROW_BALANCE) <= 0) {
            return Optional.empty();
        }
        return Optional.of(finding(
                FindingType.ESCROW_BALANCE_MISMATCH,
                oldAnalysis.currentBalance(),
                newAnalysis.currentBalance(),
                difference,
                ZERO,
                "The new-servicer opening escrow balance is inconsistent with the transfer balance.",
                List.of(
                        new Evidence("doc_old_servicer_statement", 1, "closing_escrow_balance", oldAnalysis.currentBalance()),
                        new Evidence("doc_new_servicer_statement", 1, "opening_escrow_balance", newAnalysis.currentBalance())),
                "Ask the new servicer to explain and reconcile the transferred escrow balance."));
    }
}
