package com.servicerswitch.engine.findings;

public record Evidence(String documentId, int page, String field, Object value) {}
