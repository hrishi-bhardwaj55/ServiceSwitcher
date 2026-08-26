package com.servicerswitch.engine.findings;

import java.util.Optional;

public interface FindingDetector {
    Optional<Finding> detect(ReconciliationContext context);
}
