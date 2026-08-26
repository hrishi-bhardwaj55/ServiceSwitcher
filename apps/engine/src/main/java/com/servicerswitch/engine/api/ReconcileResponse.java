package com.servicerswitch.engine.api;

import com.servicerswitch.engine.findings.Finding;
import com.servicerswitch.engine.payment.PaymentDecomposition;
import java.util.List;

public record ReconcileResponse(
    List<Finding> findings, PaymentDecomposition paymentDecomposition, String engineVersion) {}
