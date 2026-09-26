# HDL Templates

Starting points for a synthesizable SystemVerilog module and a self-checking testbench. Rename `module_name`, set the parameters, and replace the placeholder logic.

## Contents

- Module template
- Testbench template

## Module template

```systemverilog
// -----------------------------------------------------------------------------
// Module:  module_name
// Purpose: one sentence
// Clock:   clk, rising edge
// Reset:   rst_n, asynchronous assert, synchronous deassert (external synchronizer)
// Latency: N cycles from in_valid to out_valid
// -----------------------------------------------------------------------------
module module_name #(
  parameter int W = 8
) (
  input  logic         clk,
  input  logic         rst_n,
  input  logic         in_valid,
  input  logic [W-1:0] in_data,
  output logic         out_valid,
  output logic [W-1:0] out_data
);

  // ---------------------------------------------------------------- state
  logic [W-1:0] data_q, data_d;
  logic         valid_q;

  // ---------------------------------------------------------------- next-state logic
  always_comb begin
    data_d = data_q;              // defaults first: no latches
    if (in_valid) data_d = in_data;
  end

  // ---------------------------------------------------------------- registers
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      data_q  <= '0;
      valid_q <= 1'b0;
    end else begin
      data_q  <= data_d;
      valid_q <= in_valid;
    end
  end

  // ---------------------------------------------------------------- outputs
  assign out_data  = data_q;
  assign out_valid = valid_q;

endmodule
```

## Testbench template

```systemverilog
// Self-checking testbench for module_name. Prints PASS/FAIL and a summary.
`timescale 1ns/1ps
module module_name_tb;
  localparam int W = 8;
  localparam time CLK_PERIOD = 10ns;

  logic         clk = 0, rst_n = 0;
  logic         in_valid = 0;
  logic [W-1:0] in_data  = '0;
  logic         out_valid;
  logic [W-1:0] out_data;
  int           errors = 0;

  module_name #(.W(W)) dut (.*);

  always #(CLK_PERIOD/2) clk = ~clk;

  // Drive one input, then check the output one cycle later.
  task automatic apply_and_check(input logic [W-1:0] value);
    @(negedge clk);
    in_valid = 1; in_data = value;
    @(negedge clk);
    in_valid = 0;
    if (!out_valid || out_data !== value) begin
      $error("value %0h: got valid=%0b data=%0h", value, out_valid, out_data);
      errors++;
    end
  endtask

  initial begin
    repeat (3) @(negedge clk);
    rst_n = 1;

    apply_and_check('0);                       // minimum
    apply_and_check('1);                       // maximum
    apply_and_check(W'(8'hA5));                // pattern
    repeat (20) apply_and_check(W'($urandom)); // random

    if (errors == 0) $display("PASS");
    else             $display("FAIL: %0d errors", errors);
    $finish;
  end
endmodule
```
