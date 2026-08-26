package com.servicerswitch.engine.findings;

import com.servicerswitch.engine.escrow.EscrowComputation;
import com.servicerswitch.engine.model.MortgageAccount;
import com.servicerswitch.engine.payment.PaymentDecomposition;
import java.time.LocalDate;

public record ReconciliationContext(
    MortgageAccount account,
    LocalDate transferDate,
    EscrowComputation escrowComputation,
    PaymentDecomposition paymentDecomposition) {}
