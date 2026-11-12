package com.wuwei.demo.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Protected endpoint: requires Spring Security authentication (HTTP Basic).
 */
@RestController
public class HelloController {

    @GetMapping("/api/hello")
    public String hello() {
        return "Hello World";
    }
}
