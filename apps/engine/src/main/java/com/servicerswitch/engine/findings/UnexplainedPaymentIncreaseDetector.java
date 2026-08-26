package com.servicerswitch.engine.findings;

import static com.servicerswitch.engine.findings.FindingSupport.finding;
import static com.servicerswitch.engine.money.Money.TWELVE;
import static com.servicerswitch.engine.money.Money.ZERO;
import static com.servicerswitch.engine.money.Money.cents;

import com.servicerswitch.engine.payment.PaymentDecomposition;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

public final class UnexplainedPaymentIncreaseDetector implements FindingDetector {
    @Override
    public Optional<Finding> detect(ReconciliationContext context) {
        PaymentDecomposition decomposition = context.paymentDecomposition();
        if (decomposition.outcome() == FindingType.EXPLAINED) {
            return Optional.of(finding(
                    FindingType.EXPLAINED,
                    decomposition.paymentChange(),
                    decomposition.paymentChange().subtract(decomposition.residual()),
                    decomposition.residual(),
                    ZERO,
                    "The payment change is fully explained by documented components.",
                    List.of(),
                    null));
        }
        BigDecimal annualImpact = cents(decomposition.residual().multiply(TWELVE));
        return Optional.of(finding(
                FindingType.UNEXPLAINED_PAYMENT_INCREASE,
                decomposition.paymentChange(),
                decomposition.paymentChange().subtract(decomposition.residual()),
                annualImpact,
                decomposition.residual(),
                "Part of the post-transfer payment increase is not explained by supplied components.",
                List.of(
                        new Evidence("doc_old_servicer_statement", 1, "total_payment", null),
                        new Evidence("doc_new_servicer_statement", 1, "total_payment", null),
                        new Evidence("doc_escrow_analysis", 1, "new_total_payment", null)),
                "Ask the servicer for an itemized explanation of the remaining increase."));
    }
}
