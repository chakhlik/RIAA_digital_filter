import numpy as np
import wave
import math
from scipy.signal import lfilter


#open files to read and write data
#output filename same as input + '-SDF'
#framerate and nchannels derived from input file
class InOutStream:
    name_append="-SDF"
    framerate=1
    left_peak=1.0
    left_rms=1.0
    right_peak=1.0
    right_rms=1.0
    level_0db=1

    def __init__(self, filename, ku=16.0, path="", buffer_size=8192):
        self.src_file=path+filename
        self.dest_file=path+filename[0:-4]+self.name_append+".wav"
        self.src=wave.open(self.src_file, mode="r")
        self.params=self.src.getparams()
        self.dest=wave.open(self.dest_file, mode="w")
        self.dest.setparams(self.params)
        self.framerate=self.params.framerate
        self.ku=ku
        self.level_0db=2**(8*self.params.sampwidth-1)
        self.buffer_size = buffer_size

    def close_all(self):
        self.src.close()
        self.dest.close()

    def get_readout(self):
        buf = self.src.readframes(self.buffer_size)
        sampwidth = self.params.sampwidth

        if sampwidth == 3:  # 24-bit audio
            buf = np.frombuffer(buf, dtype=np.uint8).reshape(-1, 3)
            samples = (buf[:, 0].astype(np.int32) |
                       (buf[:, 1].astype(np.int32) << 8) |
                       (buf[:, 2].astype(np.int32) << 16))
            samples[samples >= 2 ** 23] -= 2 ** 24  # Приведение к знаковому int24
            samples = samples.astype(np.float32)
        else:
            dtype = np.dtype(f'int{sampwidth * 8}').newbyteorder('<')
            samples = np.frombuffer(buf, dtype=dtype).astype(np.float32)

        return samples.reshape(-1, self.params.nchannels)

    def put_readout(self, processed_samples):
        sampwidth = self.params.sampwidth
        num_channels = self.params.nchannels
        processed_samples = processed_samples * self.ku

        if sampwidth == 3:  # 24-bit audio
            # Преобразуем float32 -> int32
            processed_samples = processed_samples.astype(np.int32)
            processed_samples = np.clip(processed_samples, -2 ** 23 - 2, 2 ** 23 - 2)

            # Разбиваем 24-битные числа на 3 байта (поддержка стерео)
            buf_out = np.zeros((processed_samples.shape[0], num_channels, 3), dtype=np.uint8)
            buf_out[:, :, 0] = processed_samples & 0xFF
            buf_out[:, :, 1] = (processed_samples >> 8) & 0xFF
            buf_out[:, :, 2] = (processed_samples >> 16) & 0xFF

            buf_out = buf_out.flatten().tobytes()
        else:
            dtype = np.dtype(f'int{sampwidth * 8}').newbyteorder('<')
            processed_samples = processed_samples.astype(dtype)
            processed_samples = np.clip(processed_samples, -2 ** (sampwidth * 8 - 1) - 2, 2 ** (sampwidth * 8 - 1) - 2)
            buf_out = processed_samples.flatten().tobytes()

        self.dest.writeframes(buf_out)


#general digital filter
class DigitalFilter:

    def __init__(self, b0, b1, b2, a1, a2):
        self.samples = [0.0,0.0,0.0,0.0,0.0]
        self.coefs = [b0, b1, b2, a1, a2]


    def process(self, x):

        self.samples.pop(2)
        self.samples.insert(0,x)
        y = math.fsum(k*m for k,m in zip(self.samples,self.coefs))
        self.samples.pop(4)
        self.samples.insert(3, y)
        return y

#digital filter with RIAA response (1 or 2 channels)
class RiaaFilter:
    # main RIAA constants
    tau_318 = 318e-6
    tau_3180 = 3180e-6
    tau_75 = 75e-6
    def __init__(self, framerate):
        t_sample = 1.0 / float(framerate)
        # coefs for 20-2000 Hz part
        beta_1 = self.tau_318 / t_sample
        alfa_1 = self.tau_3180 / t_sample
        alfa_2 = self.tau_75 / t_sample
        b0 = (1.0 + beta_1) / (1.0 + alfa_1 + alfa_2)
        b1 = 1.0 / (1.0 + alfa_1 + alfa_2)
        b2 = -1.0 * beta_1 / (1.0 + alfa_1 + alfa_2)
        a1 = 1.0 / (1.0 + alfa_1 + alfa_2)  # changed sign
        a2 = -1.0 * (alfa_1 + alfa_2) / (1 + alfa_1 + alfa_2)  # changed sign
        self.b_low = np.array([b0, b1, b2])
        self.a_low = np.array([1.0, a1, a2])

        # coefs for 2000 - 22000 Hz part
        f_tau_75 = 1.0 / (2.0 * math.pi * self.tau_75)
        k = math.tan(math.pi * f_tau_75 * t_sample)
        b = k / (k + 1.0)
        a = 1.0 * (k - 1.0) / (k + 1.0)  # changed sign
        self.b_high = np.array([b, b, 0])
        self.a_high = np.array([1.0, a, 0])

        self.zi_low = np.zeros(len(self.a_low) - 1)
        self.zi_high = np.zeros(len(self.a_high) - 1)


    def process(self, x):
        # Сначала пропускаем через НЧ-фильтр
        y, self.zi_low = lfilter(self.b_low, self.a_low, x, zi=self.zi_low)
        # Потом через ВЧ-фильтр
        y, self.zi_high = lfilter(self.b_high, self.a_high, y, zi=self.zi_high)
        return y