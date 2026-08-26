package com.servicerswitch.engine;

import com.servicerswitch.engine.api.ReconcileRequest;
import com.servicerswitch.engine.api.ReconcileResponse;
import com.servicerswitch.engine.escrow.EscrowCalculator;
import com.servicerswitch.engine.escrow.EscrowComputation;
import com.servicerswitch.engine.findings.FindingRegistry;
import com.servicerswitch.engine.findings.ReconciliationContext;
import com.servicerswitch.engine.model.EscrowAnalysis;
import com.servicerswitch.engine.payment.PaymentCalculator;
import com.servicerswitch.engine.payment.PaymentDecomposition;
import org.springframework.stereotype.Service;

@Service
public class ReconciliationService {
    private static final String ENGINE_VERSION = "1.0.0";
    private final EscrowCalculator escrowCalculator = new EscrowCalculator();
    private final PaymentCalculator paymentCalculator = new PaymentCalculator();
    private final FindingRegistry registry = new FindingRegistry();

    public ReconcileResponse reconcile(ReconcileRequest request) {
        int analysisCount = request.account().escrowAnalyses().size();
        EscrowAnalysis currentAnalysis = request.account().escrowAnalyses().get(analysisCount - 1);
        int projectionYear = request.account().taxBills().stream()
                .mapToInt(bill -> bill.taxYear())
                .max()
                .orElseThrow(() -> new IllegalArgumentException("missing tax bill"));
        EscrowComputation escrow = escrowCalculator.compute(
                request.account(), currentAnalysis, projectionYear);
        PaymentDecomposition payment = paymentCalculator.decompose(
                request.account(), request.transferDate());
        ReconciliationContext context = new ReconciliationContext(
                request.account(), request.transferDate(), escrow, payment);
        return new ReconcileResponse(registry.evaluate(context), payment, ENGINE_VERSION);
    }
}
