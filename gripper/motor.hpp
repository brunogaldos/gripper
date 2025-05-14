extern Tle94112Ino controller;
int previousDirectionMotor1 =0; //1 für vorwärts, -1 für rückwärts,0 für gestoppt
int previousDirectionMotor2 =0;
void motor_pwm(int motor, int speed) {
 int currentDirection = (speed >0) ?1 : (speed <0) ? -1 :0;

 if (motor ==1) {
 if (currentDirection != previousDirectionMotor1) {
 controller.configPWM(controller.TLE_PWM1, controller.TLE_FREQ200HZ,0);
 delay(10);
 controller.clearErrors();
 previousDirectionMotor1 = currentDirection;
 }
 if (speed >0) {
 controller.configHB(controller.TLE_HB1, controller.TLE_HIGH, controller.TLE_NOPWM);
 controller.configHB(controller.TLE_HB2, controller.TLE_HIGH, controller.TLE_NOPWM);
 controller.configHB(controller.TLE_HB3, controller.TLE_LOW, controller.TLE_PWM1);
 controller.configHB(controller.TLE_HB4, controller.TLE_LOW, controller.TLE_PWM1);
 } else {
 controller.configHB(controller.TLE_HB3, controller.TLE_HIGH, controller.TLE_NOPWM);
 controller.configHB(controller.TLE_HB4, controller.TLE_HIGH, controller.TLE_NOPWM);
 controller.configHB(controller.TLE_HB1, controller.TLE_LOW, controller.TLE_PWM1);
 controller.configHB(controller.TLE_HB2, controller.TLE_LOW, controller.TLE_PWM1);
 }
 controller.clearErrors();
 controller.configPWM(controller.TLE_PWM1, controller.TLE_FREQ200HZ, abs(speed));
 } else {
 if (currentDirection != previousDirectionMotor2) {
 controller.configPWM(controller.TLE_PWM2, controller.TLE_FREQ200HZ,0);
 delay(10);
 controller.clearErrors();
 previousDirectionMotor2 = currentDirection;
 }
 if (speed >0) {
 controller.configHB(controller.TLE_HB7, controller.TLE_HIGH, controller.TLE_NOPWM);
 controller.configHB(controller.TLE_HB8, controller.TLE_HIGH, controller.TLE_NOPWM);
 controller.configHB(controller.TLE_HB9, controller.TLE_LOW, controller.TLE_PWM2);
 controller.configHB(controller.TLE_HB10, controller.TLE_LOW, controller.TLE_PWM2);
 } else {
 controller.configHB(controller.TLE_HB9, controller.TLE_HIGH, controller.TLE_NOPWM);
 controller.configHB(controller.TLE_HB10, controller.TLE_HIGH, controller.TLE_NOPWM);
 controller.configHB(controller.TLE_HB7, controller.TLE_LOW, controller.TLE_PWM2);
 controller.configHB(controller.TLE_HB8, controller.TLE_LOW, controller.TLE_PWM2);
 }
 controller.clearErrors();
 controller.configPWM(controller.TLE_PWM2, controller.TLE_FREQ200HZ, abs(speed));
 }
}
