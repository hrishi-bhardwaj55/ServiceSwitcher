package com.servicerswitch.engine.model;

import java.time.LocalDate;

public record ServicingPeriod(String servicerId, LocalDate startDate, LocalDate endDate) {}
