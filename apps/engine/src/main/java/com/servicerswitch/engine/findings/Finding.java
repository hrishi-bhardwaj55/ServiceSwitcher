package com.servicerswitch.engine.findings;

import java.math.BigDecimal;
import java.util.List;

public record Finding(
        FindingType findingType,
        Severity severity,
        double confidence,
        BigDecimal actualValue,
        BigDecimal servicerValue,
        BigDecimal difference,
        BigDecimal monthlyImpact,
        String explanation,
        List<Evidence> evidence,
        List<String> relevantSources,
        String recommendedAction) {}
