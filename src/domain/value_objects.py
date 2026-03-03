from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class CNPJ:
    value: str  # sempre só dígitos, 14 chars

    @staticmethod
    def normalize(raw: str) -> str:
        digits = re.sub(r"\D", "", raw or "")
        return digits

    @staticmethod
    def is_valid_cnpj(digits: str) -> bool:
        if not digits or len(digits) != 14:
            return False
        if digits == digits[0] * 14:
            return False

        def calc_dv(base: str, weights: list[int]) -> str:
            s = sum(int(d) * w for d, w in zip(base, weights))
            r = s % 11
            dv = "0" if r < 2 else str(11 - r)
            return dv

        w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        w2 = [6] + w1

        dv1 = calc_dv(digits[:12], w1)
        dv2 = calc_dv(digits[:12] + dv1, w2)
        return digits[-2:] == dv1 + dv2

    @staticmethod
    def is_valid_cpf(digits: str) -> bool:
        if not digits or len(digits) != 11:
            return False
        if digits == digits[0] * 11:
            return False

        def calc_dv_cpf(base: str, factor: int) -> str:
            s = sum(int(d) * (factor - i) for i, d in enumerate(base))
            r = (s * 10) % 11
            return "0" if r >= 10 else str(r)

        dv1 = calc_dv_cpf(digits[:9], 10)
        dv2 = calc_dv_cpf(digits[:10], 11)
        return digits[-2:] == dv1 + dv2

    @staticmethod
    def is_valid(digits: str) -> bool:
        return CNPJ.is_valid_cnpj(digits) or CNPJ.is_valid_cpf(digits)

    @classmethod
    def from_raw(cls, raw: str) -> "CNPJ":
        digits = cls.normalize(raw)
        if not cls.is_valid(digits):
            raise ValueError(f"CNPJ inválido: {raw}")
        return cls(value=digits)

    def masked(self) -> str:
        d = self.value
        if len(d) == 11:
            # CPF: 000.000.000-00
            return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
        # CNPJ: 00.000.000/0000-00
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"