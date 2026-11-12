package com.wuwei.demo;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class HelloWorldApplicationTests {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void helloRequiresAuthentication() throws Exception {
        mockMvc.perform(get("/api/hello"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void helloWithValidCredentials() throws Exception {
        mockMvc.perform(get("/api/hello").with(httpBasic("test", "123456")))
                .andExpect(status().isOk())
                .andExpect(content().string("Hello World"));
    }

    @Test
    void helloWithWrongPassword() throws Exception {
        mockMvc.perform(get("/api/hello").with(httpBasic("test", "wrong")))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void loginWithValidCredentials() throws Exception {
        mockMvc.perform(post("/api/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"test\",\"password\":\"123456\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("success"))
                .andExpect(jsonPath("$.username").value("test"))
                .andExpect(jsonPath("$.authorization").value("Basic dGVzdDoxMjM0NTY="));
    }

    @Test
    void loginWithInvalidCredentials() throws Exception {
        mockMvc.perform(post("/api/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"test\",\"password\":\"bad\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.status").value("error"));
    }
}
