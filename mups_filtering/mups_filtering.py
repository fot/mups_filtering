
import numpy as np


# Define MUPS valve thermistor point pair calibration table.
pp_counts = [0, 27, 36, 44, 55, 70, 90, 118, 175, 195, 210, 219, 226, 231, 235, 255]
pp_temps = [369.53, 263.32577, 239.03652, 222.30608, 203.6944, 183.2642, 161.0796, 134.93818, 85.65725, 65.6537,
            47.3176, 33.50622, 19.9373, 7.42435, -5.79635, -111.7726]
count_to_degf = np.poly1d(np.polyfit(pp_counts, pp_temps, 8))
degf_to_counts = np.poly1d(np.polyfit(pp_temps, pp_counts, 8))

# Define MUPS valve thermistor voltage point pair calibration table.
count_to_volts = np.poly1d(np.polyfit(np.arange(0, 256), np.arange(0, 5.12, 0.02), 8))
volts_to_counts = np.poly1d(np.polyfit(np.arange(0, 5.12, 0.02), np.arange(0, 256), 8))

# Volatage and Temperature, with and without resistor
volt_with_resistor = [4.153325779, 3.676396578, 3.175100371, 2.587948965, 2.435, 2.025223702, 1.538506813, 1.148359251,
                      0.63128179, 0.354868907, 0.208375569]
volt_without_resistor = [28.223, 15, 9.1231, 5.5228, 4.87, 3.467, 2.249, 1.5027, 0.7253, 0.38276, 0.21769]
temp_without_resistor = [50, 77, 100, 125, 130, 150, 175, 200, 250, 300, 350]
volt_without_resistor_to_temp_without_resistor = np.poly1d(np.polyfit(volt_without_resistor, temp_without_resistor, 8))
temp_without_resistor_to_volt_without_resistor = np.poly1d(np.polyfit(temp_without_resistor, volt_without_resistor, 8))
volt_with_resistor_to_volt_without_resistor = np.poly1d(np.polyfit(volt_with_resistor, volt_without_resistor, 8))
volt_without_resistor_to_volt_with_resistor = np.poly1d(np.polyfit(volt_without_resistor, volt_with_resistor, 8))


def correct_temperature(temp):
    """ Calculate a MUPS valve thermistor corrected temperature.

    Args:
        temp (float, int): Temperature in Fahrenheit to which a correction will be applied.

    Returns:
        (float): Corrected temperaure

    """

    # Convert observed temperature to voltage
    count = degf_to_counts(temp)
    volt = count_to_volts(count)

    # Convert voltage as read, assuming no resistor, to what it would be with the resistor
    new_volt = volt_without_resistor_to_volt_with_resistor(volt)

    # Convert this new voltage to counts and, in turn, to a new temperature
    new_count = volts_to_counts(new_volt)
    new_temp = count_to_degf(new_count)

    return new_temp


def nearest_value_signal_correction(telem):
    """ Use a nearest value algorithm to determine the true thermistor signal

    Args:
        telem (iterable): Iterable over which to apply the correction algorithm.

    Returns:
        (ndarray): Corrected signal

    NOTE: This algorithm works best if the input array starts at a known good value, with several good data values
        following the starting value.

    """
    corrected_temps = []
    truth = telem[0]
    corrected_temp = truth
    corrected_temps.append(corrected_temp)

    for n in np.arange(len(telem) - 1):
        telem_temp = telem[n + 1]
        new_temp = correct_temperature(telem_temp)

        if abs(corrected_temp - telem_temp) < abs(corrected_temp - new_temp):
            # If the difference between the previous value and the uncorrected temperature is less than the difference
            # between the previous value and the corrected temperature, use the uncorrected temperature.
            corrected_temp = telem_temp
        else:
            # If the difference between the previous value and the uncorrected temperature is larger than the difference
            # between the previous value and the corrected temperature, use the corrected temperature.
            corrected_temp = new_temp

        corrected_temps.append(corrected_temp)

    return corrected_temps