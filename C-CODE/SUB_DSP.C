/************************************************************************
*
*	FILENAME		:	sub_dsp.c
*
*	DESCRIPTION		:	General Purpose Signal Processing Library
*
************************************************************************
*
*	SUB-ROUTINES	:	- Autocorr()
*					- Az_Lsp()
*					- Back_Fil()
*					- Chebps()
*					- Convolve()
*					- Fac_Pond()
*					- Get_Lsp_Pol()
*					- Int_Lpc4()
*					- Lag_Window()
*					- Levin_32()
*					- LPC_Gain()
*					- Lsp_Az()
*					- Pond_Ai()
*					- Residu()
*					- Syn_Filt()
*
************************************************************************
*
*	INCLUDED FILES	:	source.h
*					stdio.h
*					stdlib.h
*
*					grid .tab
*					lag_wind.tab
*					window.tab
*
************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include "source.h"

#include "grid.tab"
#include "lag_wind.tab"
#include "window.tab"

/* pp = local LPC order, nc =pp/2 */
#define pp (Word16)10
#define nc (Word16)5

/* Length for local impulse response */

#define  llg     (Word16)60


/**************************************************************************
*
*	ROUTINE				:	Autocorr
*
*	DESCRIPTION			:	Compute autocorrelations
*
**************************************************************************
*
*	USAGE				:	Autocorr(buffer_in,p,buffer_out1,buffer_out2)
*							(Routine_Name(input1,input2,output1,output2))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Input signal buffer
*						- Format : Word16
*
*	INPUT2			:	- Description : LPC order
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Autocorrelations buffer (msb)
*							- Format : Word16
*
*		OUTPUT2			:	- Description : Autocorrelations buffer (lsb)
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Autocorr(Word16 x[], Word16 p, Word16 r_h[], Word16 r_l[])
{
  Word16 i, j, norm;
  Word16 y[L_window];
  Word32 sum;

  extern Flag Overflow;

  /* Windowing of signal */

  for(i=0; i<L_window; i++)
    y[i] = mult_r(x[i], window[i]);

  /* Compute r[0] and test for overflow */

  do {
    Overflow = 0;
    sum = 1;				/* Avoid case of all zeros */
    for(i=0; i<L_window; i++)
      sum = L_mac0(sum, y[i], y[i]);

    /* If overflow divide y[] by 4 */

    if(Overflow != 0)
    {
      for(i=0; i<L_window; i++)
        y[i] = shr(y[i], (Word16)2);
    }

  }while(Overflow != 0);


 /* Normalization of r[0] */

  norm = norm_l(sum);
  sum  = L_shl(sum, norm);
  sum  = L_shr(sum, (Word16)1);		/* For special double format */
  L_extract(sum, &r_h[0], &r_l[0]);

 /* r[1] to r[p] */

  for (i = 1; i <= p; i++)
  {
    sum = 0;
    for(j=0; j<L_window-i; j++)
      sum = L_mac0(sum, y[j], y[j+i]);

    sum = L_shr(sum, (Word16)1);		/* Special double format */
    sum = L_shl(sum, norm);
    L_extract(sum, &r_h[i], &r_l[i]);
  }
  return;
}

/**************************************************************************
*
*	ROUTINE				:	Az_Lsp
*
*	DESCRIPTION			:	Compute the LSPs  in the cosine domain
*							from the LPC coefficients  (order=10)
*
**************************************************************************
*
*	USAGE				:	Az_Lsp(buffer_in1,buffer_out,buffer_in2)
*							(Routine_Name(input1,output1,input2))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Predictor coefficients
*						- Format : Word16 - Q12
*
*	INPUT2			:	- Description : Previous LSP values
*							          (in case not 10 roots are found)
*						- Format : Word16 - Q15
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Line spectral pairs in the 
*								          cosine domain
*							- Format : Word16 - Q15
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Az_Lsp(Word16 a[], Word16 lsp[], Word16 old_lsp[])
{
 Word16 i, j, nf, ip;
 Word16 xlow, ylow, xhigh, yhigh, xmid, ymid, xint;
 Word16 x, y, sign, exp;
 Word16 *coef;
 Word16 f1[pp/2+1], f2[pp/2+1];
 Word32 t0;

/*-------------------------------------------------------------*
 *  find the sum and diff. pol. F1(z) and F2(z)                *
 *    F1(z) <--- F1(z)/(1+z**-1) & F2(z) <--- F2(z)/(1-z**-1)  *
 *                                                             *
 * f1[0] = 1.0;                                                *
 * f2[0] = 1.0;                                                *
 *                                                             *
 * for (i = 0; i< nc; i++)                                     *
 * {                                                           *
 *   f1[i+1] = a[i+1] + a[pp-i] - f1[i] ;                       *
 *   f2[i+1] = a[i+1] - a[pp-i] + f2[i] ;                       *
 * }                                                           *
 *-------------------------------------------------------------*/

 f1[0] = 2048;				/* f1[0] = 1.0 is in Q11 */
 f2[0] = 2048;				/* f2[0] = 1.0 is in Q11 */


 for (i = 0; i< nc; i++)
 {
   t0 = Load_sh(a[i+1], (Word16)15);	/* a[i+1]  in Q27 */
   t0 = add_sh(t0, a[pp-i], (Word16)15);	/* +a[pp-i] in Q27 */
   t0 = sub_sh16(t0, f1[i]);			/* -f1[i]  in Q27 */
   f1[i+1] = extract_h(t0);		/* f1[i+1] = a[i+1] + a[pp-i] - f1[i] */
							/* result in Q11  */

   t0 = Load_sh(a[i+1], (Word16)15);	/* a[i+1]  in Q27   */
   t0 = sub_sh(t0, a[pp-i], (Word16)15);	/* -a[pp-i] in Q27 */
   t0 = add_sh16(t0, f2[i]);			/* +f2[i] in Q27  */
   f2[i+1] = extract_h(t0);		/* f2[i+1] = a[i+1] - a[pp-i] + f2[i] */
							/* result in Q11  */
 }

/*-------------------------------------------------------------*
 * find the LSPs using the Chebichev pol. evaluation           *
 *-------------------------------------------------------------*/

 nf=0;          /* number of found frequencies */
 ip=0;          /* indicator for f1 or f2      */

 coef = f1;

 xlow = grid[0];
 ylow = Chebps(xlow, coef, nc);

 j = 0;
 while ( (nf < pp) && (j < grid_points) )
 {
   j++;
   xhigh = xlow;
   yhigh = ylow;
   xlow  = grid[j];
   ylow  = Chebps(xlow,coef,nc);

   if ( L_mult0(ylow,yhigh) <= (Word32)0)
   {

     /* divide 4 times the interval */

     for (i = 0; i < 4; i++)
     {
       t0   = Load_sh(xlow, (Word16)15);	/* xmid = 0.5*(xlow + xhigh) */
       t0   = add_sh(t0, xhigh, (Word16)15);
       xmid = extract_h(t0);

       ymid = Chebps(xmid,coef,nc);

       if ( L_mult0(ylow,ymid) <= (Word32)0)
       {
         yhigh = ymid;
         xhigh = xmid;
       }
       else
       {
         ylow = ymid;
         xlow = xmid;
       }
     }


    /*-------------------------------------------------------------*
     * Linear interpolation                                        *
     *    xint = xlow - ylow*(xhigh-xlow)/(yhigh-ylow);            *
     *-------------------------------------------------------------*/

     x   = sub(xhigh, xlow);
     y   = sub(yhigh, ylow);

     if(y == 0)
     {
       xint = xlow;
     }
     else
     {
       sign= y;
       y   = abs_s(y);
       exp = norm_s(y);
       y   = shl(y, exp);
       y   = div_s( (Word16)16383, y);
       t0  = L_mult0( x, y);
       t0  = L_shr(t0, sub((Word16)19,exp) );
       y    = extract_l(t0);		/* y= (xhigh-xlow)/(yhigh-ylow) in Q10 */

       if(sign < 0) y = negate(y);

       t0   = Load_sh(xlow, (Word16)10);	/* xint = xlow - ylow*y */
       t0   = L_msu0(t0, ylow, y);
       xint = store_hi(t0, (Word16)6);

     }

     lsp[nf] = xint;
     xlow    = xint;
     nf++;

     if(ip == 0)
     {
       ip = 1;
       coef = f2;
     }
     else
     {
       ip = 0;
       coef = f1;
     }
     ylow = Chebps(xlow,coef,nc);

   }
 }

 /* Check if pp roots found */

 if( sub(nf, pp) < 0)
 {
    for(i=0; i<pp; i++)
       lsp[i] = old_lsp[i];
    printf("\n !!Not 10 roots found in Az_Lsp()!!!n");
 }

 return;
}


/**************************************************************************
*
*	ROUTINE				:	Back_Fil
*
*	DESCRIPTION			:	Perform the Backward filtering of input vector
*						buffer_in1 with buffer_in2 and write the result 
*						in output vector buffer_out.
*							All vectors are of length L
*
**************************************************************************
*
*	USAGE				:	Back_Fil(buffer_in1,buffer_in2,buffer_out,L)
*							(Routine_Name(input1,input2,output1,input3))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Input vector
*						- Format : Word16
*
*	INPUT2			:	- Description : Impulse response
*						- Format : Word16 - Q12
*
*	INPUT3			:	- Description : Vector size
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Backward filtering result
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Back_Fil(Word16 x[], Word16 h[], Word16 y[], Word16 L)
{
   Word16 i, j;
   Word32 s, max;
   Word32 y32[60];		/* Usually, dynamic allocation of L */

   /* first keep the result on 32 bits and find absolute maximum */

   max = 0;

   for (i = 0; i < L; i++)
   {
     s = 0;
     for (j = i; j <  L; j++)
       s = L_mac0(s, x[j], h[j-i]);

     y32[i] = s;

     s = L_abs(s);
     if(L_sub(s, max) > 0) max = s;
   }


   /* Find the number of right shifts to do on y32[]  */
   /* so that maximum is on 13 bits                   */

   j = norm_l(max);
   if( sub(j,(Word16)16) > 0) j = 16;

   j = sub((Word16)18, j);

   for(i=0; i<L; i++)
     y[i] = extract_l( L_shr(y32[i], j) );

   return;
}

/**************************************************************************
*
*	ROUTINE				:	Chebps
*
*	DESCRIPTION			:	Evaluate the Chebishev polynomial series
*
**************************************************************************
*
*	USAGE				:	Chebps(x,buffer_in,n)
*							(Routine_Name(input1,input2,input3))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Input value of evaluation
*							          x = cos(frequency)
*						- Format : Word16 - Q15
*
*	INPUT2			:	- Description : Coefficients of the polynomial series
*						- Format : Word16 - Q11
*
*	INPUT3			:	- Description : Polynomial order
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	- Description : Value of the polynomial C(x)
*							- Format : Word16 - Q14
*							     (saturated to +/- 1.99)
*
*	COMMENTS			:	- The polynomial order is :
*						n = p/2   (p is the prediction order)
*
*						- The polynomial is given by :
*							C(x)=T_n(x)+f(1)T_n-1(x)+...+f(n-1)T_1(x)+ f(n)/2
*
**************************************************************************/

Word16 Chebps(Word16 x, Word16 f[], Word16 n)
{
  Word16 i, cheb;
  Word16 b0_h, b0_l, b1_h, b1_l, b2_h, b2_l;
  Word32 t0;

 /* Note: All computation are done in Q24. */

  b2_h = 512;					/* b2 = 1.0 in Q24 DPF */
  b2_l = 0;

  t0 = Load_sh( x,(Word16)10);		/* 2*x in Q24          */
  t0 = add_sh( t0, f[1], (Word16)13);	/* + f[1] in Q24       */
  L_extract(t0, &b1_h, &b1_l);		/* b1 = 2*x + f[1]     */

  for (i = 2; i<n; i++)
  {
    t0 = mpy_mix(b1_h, b1_l, x);		/* t0 = x*b1                  */
    t0 = L_shl(t0,(Word16)1);			/* t0 = 2.0*x*b1              */
    t0 = sub_sh(t0, b2_l, (Word16)0);	/* t0 = 2.0*x*b1 - b2         */
    t0 = sub_sh(t0, b2_h, (Word16)15);
    t0 = add_sh(t0, f[i], (Word16)13);	/* t0 = 2.0*x*b1 - b2 + f[i]; */


    L_extract(t0, &b0_h, &b0_l);		/* b0 = 2.0*x*b1 - b2 + f[i]; */
    b2_l = b1_l;					/* b2 = b1; */
    b2_h = b1_h;
    b1_l = b0_l;					/* b1 = b0; */
    b1_h = b0_h;
  }
  t0 = mpy_mix(b1_h, b1_l, x);		/* t0    = x*b1;     */
  t0 = sub_sh(t0, b2_l, (Word16)0);		/* t0   -= b2;       */
  t0 = sub_sh(t0, b2_h, (Word16)15);
  t0 = add_sh(t0, f[n], (Word16)12);	/* t0   += 0.5*f[n]; */

  t0 = L_shl(t0, (Word16)6);			/* Q24 to Q30 with saturation */
  cheb = extract_h(t0);				/* Result in Q14           */

  return(cheb);
}

/**************************************************************************
*
*	ROUTINE				:	Convolve
*
*	DESCRIPTION			:	Perform the convolution between two input vectors
*						buffer_in1 and buffer_in2 and write the result in
*						output vector buffer_out.
*							All vectors are of length L
*
**************************************************************************
*
*	USAGE				:	Convolve(buffer_in1,buffer_in2,buffer_out,L)
*							(Routine_Name(input1,input2,output1,input3))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Input vector
*						- Format : Word16
*
*	INPUT2			:	- Description : Impulse response
*						- Format : Word16 - Q12
*
*	INPUT3			:	- Description : Vector size
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Output vector
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Convolve(Word16 x[], Word16 h[], Word16 y[], Word16 L)
{
   Word16 i, n;
   Word32 s;

   for (n = 0; n < L; n++)
   {
     s = 0;
     for (i = 0; i <= n; i++)
       s = L_mac0(s, x[i], h[n-i]);
     y[n] = store_hi(s, (Word16)4);		/* h is in Q12 */
   }

   return;
}


/**************************************************************************
*
*	ROUTINE				:	Fac_Pond
*
*	DESCRIPTION			:	Compute LPC spectral expansion factors (fac[])
*							with the LPC order fixed to 10
*
**************************************************************************
*
*	USAGE				:	Fac_Pond(gamma,buffer_out)
*							(Routine_Name(input1,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Spectral expansion
*						- Format : Word16 - Q15
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Computed expansion factors
*							- Format : Word16 - Q15
*
*	RETURNED VALUE		:	None
*
*	COMMENTS			:	- fac[0] = gamma
*							- fac[i] = fac[i-1] * gamma	i=1,9
*
**************************************************************************/

void Fac_Pond(Word16 gamma, Word16 fac[])
{
  Word16 i;

  fac[0] = gamma;
  for(i=1; i<pp; i++)
    fac[i] = round( L_mult(fac[i-1], gamma) );

  return;
}


/**************************************************************************
*
*	ROUTINE				:	Get_Lsp_Pol
*
*	DESCRIPTION			:	Find the polynomial F1(z) or F2(z) from the LSPs
*
**************************************************************************
*
*	USAGE				:	Get_Lsp_Pol(buffer_in,buffer_out)
*							(Routine_Name(input1,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : line spectral pairs 
*							          (cosine domaine)
*						- Format : Word16 - Q15
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Coefficients of F1 or F2 
*							- Format : Word32 - Q24
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Get_Lsp_Pol(Word16 *lsp, Word32 *f)
{
  Word16 i,j, hi, lo;
  Word32 t0;

   /* Computation in Q24 */

   *f = Load_sh((Word16)4096,(Word16)12);	/* f[0] = 1.0;           in Q24  */
   f++;
   *f = 0;
   *f = sub_sh(*f, *lsp, (Word16)10);	/* f[1] = -2.0 * lsp[0]; in Q24  */
   f++;
   lsp += 2;					/* Advance lsp pointer           */

   for(i=2; i<=5; i++)
   {
     *f = f[-2];

     for(j=1; j<i; j++, f--)
     {
       L_extract(f[-1] ,&hi, &lo);
       t0 = mpy_mix(hi, lo, *lsp);		/* t0 = f[-1] * lsp    */
       t0 = L_shl(t0, (Word16)1);
       *f = L_add(*f, f[-2]);			/* *f += f[-2]         */
       *f = L_sub(*f, t0);			/* *f -= t0            */
     }
     *f   = sub_sh(*f, *lsp, (Word16)10);	/* *f -= lsp<<10       */
     f   += i;					/* Advance f pointer   */
     lsp += 2;					/* Advance lsp pointer */
   }

   return;
}


/**************************************************************************
*
*	ROUTINE				:	Int_Lpc4
*
*	DESCRIPTION			:	Perform the LPC interpolation for the 4 sub-frames.
*							The interpolation is done on the LSP computed 
*							in the cosine domain 
*
**************************************************************************
*
*	USAGE				:	Int_Lpc4(buffer_in1,buffer_in2,buffer_out)
*							(Routine_Name(input1,input2,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : LSP of previous frame
*						- Format : Word16
*
*	INPUT2			:	- Description : LSP of current frame
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : LPC coeff. vector for the 4 sub-frames
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Int_Lpc4(Word16 lsp_old[], Word16 lsp_new[], Word16 a[])
{
  Word16 i, j, fac_new, fac_old;
  Word16 lsp[pp];
  Word32 t0;

  fac_new = 8192;       /* 1/4 in Q15 */
  fac_old = 24576;      /* 3/4 in Q15 */

  for(j=0; j<33; j+=11)
  {
    for(i=0; i<pp; i++)
    {
      t0 = L_mult(lsp_old[i], fac_old);
      t0 = L_mac(t0, lsp_new[i], fac_new);
      lsp[i] = extract_h(t0);
    }
    Lsp_Az(lsp, &a[j]);

    fac_old = sub(fac_old, (Word16)8192);
    fac_new = add(fac_new, (Word16)8192);
  }
  Lsp_Az(lsp_new, &a[33]);

  return;
}

/**************************************************************************
*
*	ROUTINE				:	Lag_Window
*
*	DESCRIPTION			:	Lag_window on autocorrelations
*
**************************************************************************
*
*	USAGE				:	Lag_Window(p,buffer1,buffer2)
*							(Routine_Name(input1,arg2,arg3))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description :  LPC order
*						- Format : Word16
*
*	ARG2				:	- Description : Autocorrelations (msb)
*						- Format : Word16
*
*	ARG3				:	- Description : Autocorrelations (lsb)
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*	ARG2				:	- Description : Lag_Windowed autocorrelations (msb)
*						- Format : Word16
*
*	ARG3				:	- Description : Lag_Windowed autocorrelations (lsb)
*						- Format : Word16
*
*	RETURNED VALUE		:	None
*
*	COMMENTS			:	r[i] *= lag_wind[i]
*
*						r[i] and lag_wind[i] are in special extended precision
*						(for details on this format, see "comments" 
*						in the header of the file fexp_tet.c - Section A.5.2)
*
**************************************************************************/

void Lag_Window(Word16 p, Word16 r_h[], Word16 r_l[])
{
  Word16 i;
  Word32 x;

  for(i=1; i<=p; i++)
  {
     x  = mpy_32(r_h[i], r_l[i], lag_h[i-1], lag_l[i-1]);
     L_extract(x, &r_h[i], &r_l[i]);
  }
  return;
}


/**************************************************************************
*
*	ROUTINE				:	Levin_32
*
*	DESCRIPTION			:	Computation of 10 LPC coefficients
*							based on the Levison-Durbin algorithm
*							in double precision
*
**************************************************************************
*
*	USAGE				:	Levin_32(buffer_in1,buffer_in2,buffer_out)
*							(Routine_Name(input1,input2,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Vector of autocorrelations (msb)
*						- Format : Word16 - 11 values
*
*	INPUT2			:	- Description : Vector of autocorrelations (lsb)
*						- Format : Word16 - 11 values
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : LPC coefficients
*							- Format : Word16 - Q12
*
*	RETURNED VALUE		:	None
*
*	COMMENTS			:	Algorithm :
*
*							R[i]	autocorrelations
*							A[i]	filter coefficients
*							K 	reflection coefficients
*							Alpha	prediction gain.
*
*						Initialisations :
*
*							A[0] = 1
*							K    = -R[1]/R[0]
*							A[1] = K
*							Alpha = R[0] * (1-K**2]
*
*						DO for  i = 2 to pp
*
*							S =  SUM ( R[j]*A[i-j] ,j=1,i-1 ) +  R[i]
*							K = -S / Alpha
* 							An[j] = A[j] + K*A[i-j]   for j=1 to i-1
*								where   An[i] = new A[i]
*							An[i]=K
*							Alpha=Alpha * (1-K**2)
*
*						END
*
**************************************************************************


**************************************************************************
*
*	NOTES ON THE DYNAMICS OF THE COMPUTATIONS	:
*
*	The numbers used are in double precision with the following format :
*
*	A = AH <<15 + AL.  AH and AL are 16 bit signed integers. Since the LSB's also contain *	a sign bit, this format does not correspond to standard 32 bit integers.  This format is used *	since it allows fast execution of multiplications and divisions.
*
*	"DPF" will refer to this special format in the following text.
*	(for details on this format, see "comments" in the header of file fexp_tet.c - Section A.5.2)
*
*	The R[i] were normalized in routine Autocorr (hence, R[i] < 1.0).
*	The K[i] and Alpha are theoretically < 1.0.
*	The A[i], for a sampling frequency of 8 kHz, are in practice always inferior to 16.0.
*
*	These characteristics allow straigthforward fixed-point implementation.  The parameters are *	represented as follows :
*
*	R[i]    Q30   +- .99..
*	K[i]    Q30   +- .99..
*	Alpha   Normalised -> mantissa in Q30 plus exponant
*	A[i]    Q26   +- 15.999..
*
*	The additions are performed in 32 bit.  For the summation used to compute the K[i], 
*	numbers in Q30 are multiplied by numbers in Q26, with the results of the multiplications in *	Q26, resulting in a dynamic of +/- 32.  This is sufficient to avoid overflow, since the final
*	result of the summation is necessarily < 1.0 as both the K[i] and Alpha are 
*	theoretically < 1.0.
*
**************************************************************************/

/* Last A(z) for case of unstable filter */

static Word16 old_A[pp+1]={4096,0,0,0,0,0,0,0,0,0,0};

void Levin_32(Word16 Rh[], Word16 Rl[], Word16 A[])
{
 Word16 i, j;
 Word16 hi, lo;
 Word16 Kh, Kl;              	/* reflexion coefficient; hi and lo          */
 Word16 alp_h, alp_l, alp_e;	/* Prediction gain; hi lo and exponant       */
 Word16 Ah[pp+1], Al[pp+1];	/* LPC coef. in double prec.                 */
 Word16 Anh[pp+1], Anl[pp+1];	/* LPC coef.for next iterat. in double prec. */
 Word32 t0, t1, t2;		/* temporary variable                        */


/* K = A[1] = -R[1] / R[0] */

  t1  = L_comp(Rh[1], Rl[1]);			/* R[1] in Q30      */
  t2  = L_abs(t1);				/* abs R[1]         */
  t0  = div_32(t2, Rh[0], Rl[0]);		/* R[1]/R[0] in Q30 */
  if(t1 > 0) t0= L_negate(t0);		/* -R[1]/R[0]       */
  L_extract(t0, &Kh, &Kl);			/* K in DPF         */
  t0 = L_shr(t0,(Word16)4);			/* A[1] in Q26      */
  L_extract(t0, &Ah[1], &Al[1]);		/* A[1] in DPF      */


/*  Alpha = R[0] * (1-K**2) */

  t0 = mpy_32(Kh ,Kl, Kh, Kl);		/* K*K      in Q30 */
  t0 = L_abs(t0);					/* Some case <0 !! */
  t0 = L_sub( (Word32)0x3fffffff, t0 );	/* 1 - K*K  in Q30 */
  L_extract(t0, &hi, &lo);			/* DPF format      */
  t0 = mpy_32(Rh[0] ,Rl[0], hi, lo);	/* Alpha in Q30    */

/* Normalize Alpha */

  t0 = norm_v(t0, (Word16)12, &i);
  t0 = L_shr(t0, (Word16)1);
  L_extract(t0, &alp_h, &alp_l);		/* DPF format    */
  alp_e = i-1;					/* t0 was in Q30 */

/*--------------------------------------*
 * ITERATIONS  I=2 to pp                *
 *--------------------------------------*/

  for(i= 2; i<=pp; i++)
  {

    /* t0 = SUM ( R[j]*A[i-j] ,j=1,i-1 ) +  R[i] */

    t0 = 0;
    for(j=1; j<i; j++)
      t0 = L_add(t0, mpy_32(Rh[j], Rl[j], Ah[i-j], Al[i-j]));

    t0 = L_shl(t0,(Word16)4);			/* result in Q26->convert to Q30 */
							/* No overflow possible          */
    t1 = L_comp(Rh[i],Rl[i]);
    t0 = L_add(t0, t1);				/* add R[i] in Q30               */

    /* K = -t0 / Alpha */

    t1 = L_abs(t0);
    t2 = div_32(t1, alp_h, alp_l);		/* abs(t0)/Alpha                 */
    if(t0 > 0) t2= L_negate(t2);		/* K =-t0/Alpha                  */
    t2 = L_shl(t2, alp_e);			/* denormalize; compare to Alpha */
    L_extract(t2, &Kh, &Kl);			/* K in DPF                      */

    /* Test for unstable filter, if unstable keep old A(z) */

    if ( abs_s(Kh) > 32750)
    {
       for(j=0; j<=pp; j++) A[j] = old_A[j];
       return;
     }


     /*------------------------------------------*
     *  Compute new LPC coeff. -> An[i]         *
     *  An[j]= A[j] + K*A[i-j]     , j=1 to i-1 *
     *  An[i]= K                                *
     *------------------------------------------*/


    for(j=1; j<i; j++)
    {
      t0 = mpy_32(Kh, Kl, Ah[i-j], Al[i-j]);
      t0 = add_sh(t0, Ah[j], (Word16)15);
      t0 = add_sh(t0, Al[j], (Word16)0);
      L_extract(t0, &Anh[j], &Anl[j]);
    }
    t2 = L_shr(t2, (Word16)4);		/* t2 = K in Q30->convert to Q26 */
    L_extract(t2, &Anh[i], &Anl[i]);	/* An[i] in Q26                  */

    /*  Alpha = Alpha * (1-K**2) */

    t0 = mpy_32(Kh ,Kl, Kh, Kl);		/* K*K      in Q30 */
    t0 = L_abs(t0);				/* Some case <0 !! */
    t0 = L_sub( (Word32)0x3fffffff, t0 );	/* 1 - K*K  in Q30 */
    L_extract(t0, &hi, &lo);			/* DPF format      */
    t0 = mpy_32(alp_h , alp_l, hi, lo);	/* Alpha in Q30    */

    /* Normalize Alpha */

    t0 = norm_v(t0, (Word16)12, &j);
    t0 = L_shr(t0, (Word16)1);
    L_extract(t0, &alp_h, &alp_l);		/* DPF format    */
    alp_e += j-1;					/* t0 was in Q30 */

    /* A[j] = An[j]   Note: can be done with pointers */

    for(j=1; j<=i; j++)
    {
      Ah[j] =Anh[j];
      Al[j] =Anl[j];
    }
  }

  /* Troncate A[i] in Q26 to Q12 with rounding */

  A[0] = 4096;
  for(i=1; i<=pp; i++)
  {
    t0   = L_comp(Ah[i], Al[i]);
    t0   = add_sh(t0, (Word16)1, (Word16)13);	/* rounding */
    old_A[i] = A[i] = store_hi(t0,(Word16)2);
  }

  return;
}


/**************************************************************************
*
*	ROUTINE				:	Lpc_Gain
*
*	DESCRIPTION			:	Compute energy of impulse response of 1/A(z)
*							on 60 points
*
**************************************************************************
*
*	USAGE				:	Lpc_Gain(buffer_in)
*							(Routine_Name(input1))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : LPC coefficients
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	- Description : Energy of impulse response of 1/A(z)
*							- Format : Word32 - Q20
*
**************************************************************************/

Word32 Lpc_Gain(Word16 a[])
{
  Word16 i;
  Word32 ener;
  Word16 h[llg];

  /* Compute the impulse response of A(z) */

  h[0] = 1024;				/* 1.0 in Q10 */
  for(i=1; i<llg; i++) h[i]=0;
  Syn_Filt(a, h, h, llg, &h[1], (Word16)0);

  /* Compute the energy of the impulse response */

  ener = 0;
  for(i=0; i<llg; i++)
    ener = L_mac0(ener, h[i], h[i]);

  return(ener);
}


/**************************************************************************
*
*	ROUTINE				:	Lsp_Az
*
*	DESCRIPTION			:	Compute the LPC coefficients  
*							from the LSPs in the cosine domain
*							(order=10)
*
**************************************************************************
*
*	USAGE				:	Lsp_Az(buffer_in,buffer_out)
*							(Routine_Name(input1,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Line spectral pairs in the 
*								          cosine domain
*						- Format : Word16 - Q15
*
*	OUTPUT ARGUMENT(S)		:	
*
*	OUTPUT1			:	- Description : Predictor coefficients
*							- Format : Word16 - Q12
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Lsp_Az(Word16 lsp[], Word16 a[])
{
  Word16 i, j;
  Word32 f1[6], f2[6];
  Word32 t0;

  Get_Lsp_Pol(&lsp[0],f1);
  Get_Lsp_Pol(&lsp[1],f2);

  for (i = 5; i > 0; i--)
  {
    f1[i] = L_add(f1[i], f1[i-1]);			/* f1[i] += f1[i-1]; */
    f2[i] = L_sub(f2[i], f2[i-1]);			/* f2[i] -= f2[i-1]; */
  }

  a[0] = 4096;
  for (i = 1, j = 10; i <= 5; i++, j--)
  {
    t0   = L_add(f1[i], f2[i]);			/* f1[i] + f2[i] */
    a[i] = extract_l( L_shr_r(t0,(Word16)13) );	/*from Q24 to Q12 and * 0.5*/
    t0   = L_sub(f1[i], f2[i]);			/* f1[i] - f2[i] */
    a[j] = extract_l( L_shr_r(t0,(Word16)13) );	/*from Q24 to Q12 and * 0.5*/
  }

  return;
}


/**************************************************************************
*
*	ROUTINE				:	Pond_Ai
*
*	DESCRIPTION			:	Compute spectral expansion (a_exp[]) of LPC 
*							coefficients (a[]) using spectral expansion
*							factors (fac[]) with the LPC order fixed to 10
*
**************************************************************************
*
*	USAGE				:	Pond_Ai(buffer_in1,buffer_in2,buffer_out)
*							(Routine_Name(input1,input2,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : LPC coefficients
*						- Format : Word16
*
*	INPUT2			:	- Description : Spectral expansion factors
*						- Format : Word16 - Q15
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Spectral expanded LPC coefficients
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
*	COMMENTS			:	- a_exp[i] = a[i] * fac[i-1]	i=1,10
*
**************************************************************************/

void Pond_Ai(Word16 a[], Word16 fac[], Word16 a_exp[])
{
  Word16 i;

  a_exp[0] = a[0];
  for(i=1; i<=pp; i++)
    a_exp[i] = round( L_mult(a[i], fac[i-1]) );

  return;
}


/**************************************************************************
*
*	ROUTINE				:	Residu
*
*	DESCRIPTION			:	Compute the LPC residual  by filtering the input
*							speech through A(z)
*
**************************************************************************
*
*	USAGE				:	Residu(buffer_in1,buffer_in2,buffer_out,lg)
*							(Routine_Name(input1,input2,output1,input3))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Prediction coefficients
*						- Format : Word16 - Q12
*
*	INPUT2			:	- Description : Input speech - values of buffer_in2[]
*							          from -p to -1 are needed
*						- Format : Word16
*
*	INPUT3			:	- Description : Size of filtering
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Residual signal
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Residu(Word16 a[], Word16 x[], Word16 y[], Word16 lg)
{
  Word16 i, j;
  Word32 s;

  for (i = 0; i < lg; i++)
  {
    s = Load_sh(x[i], (Word16)12);
    for (j = 1; j <= pp; j++)
      s = L_mac0(s, a[j], x[i-j]);

    s = add_sh(s, (Word16)1, (Word16)11);		/* Rounding */
    s = L_shl(s, (Word16)4);				/* Saturation */
    y[i] = extract_h(s);
  }
  return;
}


/**************************************************************************
*
*	ROUTINE				:	Syn_Filt
*
*	DESCRIPTION			:	Perform the synthesis filtering 1/A(z)
*
**************************************************************************
*
*	USAGE				:	Syn_Filt(buffer_in1,buffer_in2,buffer_out,
*							lg,buffer,flag)
*							(Routine_Name(input1,input2,output1,
*							input3,arg4,input5))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Prediction coefficients
*						- Format : Word16 - Q12
*
*	INPUT2			:	- Description : Input signal
*						- Format : Word16
*
*	INPUT3			:	- Description : Size of filtering
*						- Format : Word16
*
*	ARG4				:	- Description : Memory associated with this filtering
*						- Format : Word16
*
*		INPUT5			:	- Description :	- flag = 0  -> no update of memory
*									- flag = 1  -> update of memory
*							- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Output signal
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Syn_Filt(Word16 a[], Word16 x[], Word16 y[], Word16 lg, Word16 mem[],
              Word16 update)
{
  Word16 i, j;
  Word32 s;
  Word16 tmp[80];	/* This is usually done by memory allocation (lg+pp) */
  Word16 *yy;

  /* Copy mem[] to yy[] */

  yy = tmp;

  for(i=0; i<pp; i++)
    *yy++ = mem[i];


  /* Do the filtering. */

  for (i = 0; i < lg; i++)
  {
    s = Load_sh(x[i], (Word16)12);				/* a[] is in Q12 */
    for (j = 1; j <= pp; j++)
      s = L_msu0(s, a[j], yy[-j]);

    s     = add_sh(s, (Word16)1, (Word16)11);		/* Rounding */
    *yy++ = extract_h( L_shl(s, (Word16)4) );
  }

  for(i=0; i<lg; i++) y[i] = tmp[i+pp];

  /* Update of memory if update==1 */

  if(update != 0)
     for (i = 0; i < pp; i++) mem[i] = y[lg-pp+i];

 return;
}

