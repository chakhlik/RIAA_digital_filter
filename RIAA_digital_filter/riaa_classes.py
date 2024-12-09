import wave
import math

#open files to read and write data
#output filename same as input + '-SDF'
#framerate and nchannels derived from input file
class InOutStream:
    name_append="-SDF"
    framerate=1
    left_peak=0.0
    left_rms=0.0
    right_peak=0.0
    right_rms=0.0
    level_0db=0

    def __init__(self, filename, ku=16.0, path=""):
        self.src_file=path+filename
        self.dest_file=path+filename[0:-4]+self.name_append+".wav"
        self.src=wave.open(self.src_file, mode="r")
        self.params=self.src.getparams()
        self.dest=wave.open(self.dest_file, mode="w")
        self.dest.setparams(self.params)
        self.framerate=self.params.framerate
        self.ku=ku
        self.level_0db=2**(8*self.params.sampwidth-1)

    def close_all(self):
        self.src.close()
        self.dest.close()

    def get_readout(self):
        buf = self.src.readframes(1)
        r=[]
        r.append(float(int.from_bytes(buf[0:3], 'little', signed=True)))
        if self.params.nchannels==2:
            r.append(float(int.from_bytes(buf[3:6], 'little', signed=True)))
        return r

    def put_readout(self, *args):
        b=[]
        b.append(int(round(args[0] * self.ku, 0)).to_bytes(4, 'little', signed=True)[0:self.params.sampwidth])
        self.left_peak = max(self.left_peak, abs(args[0] * self.ku))
        self.left_rms += (args[0] * self.ku)**2
        if self.params.nchannels == 2:
            b.append(int(round(args[1] * self.ku, 0)).to_bytes(4, 'little', signed=True)[0:self.params.sampwidth])
            self.right_peak = max(self.right_peak, abs(args[1] * self.ku))
            self.right_rms += (args[1] * self.ku) ** 2
        buf_out = b''.join(b)
        self.dest.writeframesraw(buf_out)


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
        a1 = -1.0 / (1.0 + alfa_1 + alfa_2)  # changed sign
        a2 = 1.0 * (alfa_1 + alfa_2) / (1 + alfa_1 + alfa_2)  # changed sign
        # coefs for 2000 - 22000 Hz part
        f_tau_75 = 1.0 / (2.0 * math.pi * self.tau_75)
        k = math.tan(math.pi * f_tau_75 * t_sample)
        b = k / (k + 1.0)
        a = -1.0 * (k - 1.0) / (k + 1.0)  # changed sign
        self.riaa_low = DigitalFilter(b0, b1, b2, a1, a2)
        self.riaa_high = DigitalFilter(b, b, 0, a, 0)
    def process(self, x):
        y1 = self.riaa_low.process(x)
        y2 = self.riaa_high.process(y1)
        return y2
