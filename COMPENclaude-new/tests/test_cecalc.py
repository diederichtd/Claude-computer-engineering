"""Known-answer tests for cecalc. Run: python3 -m unittest discover tests"""
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "compenclaude" / "scripts" / "cecalc.py"


def run(*args: str) -> str:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, check=True).stdout


class KnownAnswers(unittest.TestCase):
    def test_twos_complement(self):
        out = run("conv", "-1", "--bits", "8")
        self.assertIn("0xFF", out)
        self.assertIn("255", out)
        self.assertIn("-56", run("conv", "200", "--bits", "8"))

    def test_endianness(self):
        self.assertIn("EF BE AD DE", run("conv", "0xDEADBEEF"))

    def test_float_encode_decode(self):
        self.assertIn("0x3DCCCCCD", run("float", "0.1"))
        self.assertIn("3.1415927410125732421875", run("float", "0x40490fdb", "--hex"))
        self.assertIn("0x3FB999999999999A", run("float", "0.1", "--double"))
        self.assertIn("+inf", run("float", "1e40"))

    def test_cache_geometry(self):
        out = run("cache", "--size", "32KiB", "--block", "64", "--assoc", "8")
        self.assertIn("64 x 8", out)
        self.assertIn("tag bits                20", out)

    def test_cache_trace(self):
        out = run("cache", "--size", "64", "--block", "16", "--addr-bits", "8",
                  "--trace", "0x00", "0x10", "0x40", "0x00")
        self.assertIn("hits 0/4", out)
        self.assertIn("conflict 1", out)

    def test_amat(self):
        self.assertIn("AMAT                    2.5", run("amat", "--levels", "1:0.05", "10:0.2", "--mem", "100"))

    def test_cpu(self):
        out = run("cpu", "--ic", "2G", "--mix", "0.5:1,0.3:2,0.2:5", "--clock", "3GHz")
        self.assertIn("2.1", out)
        self.assertIn("1.4 s", out)

    def test_amdahl(self):
        out = run("amdahl", "--fraction", "0.8", "--speedup", "10", "--target", "4")
        self.assertIn("3.57143x", out)
        self.assertIn("16x", out)

    def test_vm(self):
        self.assertIn("9+9+9+9 + 12", run("vm", "--va-bits", "48", "--page", "4KiB", "--pte", "8"))

    def test_subnet(self):
        out = run("subnet", "192.168.1.77/26")
        self.assertIn("192.168.1.127", out)
        self.assertIn("usable hosts            62", out)
        self.assertIn("/26", run("subnet", "--hosts", "50"))

    def test_timer_and_baud(self):
        self.assertIn("reload 15999", run("timer", "--clock", "16MHz", "--target", "1kHz"))
        self.assertIn("-3.549%", run("baud", "--clock", "16MHz", "--baud", "115200"))

    def test_hamming_and_crc(self):
        self.assertIn("0110011", run("hamming", "1011"))
        self.assertIn("bit 5 flipped", run("hamming", "0110111", "--check"))
        self.assertIn("remainder               100", run("crc", "--data", "11010011101100", "--poly", "1011"))


if __name__ == "__main__":
    unittest.main()
