/************************************************************************
*	FILENAME		:	init_params.c
*
*	DESCRIPTION		:	Initialisation for speech channel decoding
*
************************************************************************
*
*	SUBROUTINES		:	- init_params()
*
************************************************************************
*
*	INCLUDED FILES	:	arrays.tab
*					arrays_TETRA.tab
*					arrays_AMR475.tab
*					channel.h
*					const.tab
*					const_TETRA.tab
*					const_AMR475.tab
*					stdlib.h
*
************************************************************************/

#include <stdlib.h>
#include "source.h"
#include "globals.h"
#include "const.tab" /* contains constants for channel coding/decoding */
#include "arrays.h" /* contains constants for channel coding/decoding */

#include "const_TETRA.tab"   /* contains constants for channel coding/decoding */
#include "arrays_TETRA.tab"  /* contains arrays for channel coding/decoding */

#include "const_AMR475.tab"   /* contains constants for channel coding/decoding */
#include "arrays_AMR475.tab"  /* contains arrays for channel coding/decoding */

#define ALLOW_NEG(x) (((x) < 0) ? (((-x)%2 == 1) ?  (-x)/2 - N1_2 + 1 :  (x)/2 + 1) : (x))

void init_params(int CoderType)
{
  int i,j;
  
  switch (CoderType)
  {
    case 1:	SpFrms_per_TDMFrm = 3;
    
           Fs_SpFrms_per_TDMFrm = Fs_SpFrms_per_TDMFrm_AMR475;

    
    		N0 = N0_AMR475;
    		N1 = N1_AMR475;
    		N2 = N2_AMR475;
    		N0_2 = N0_2_AMR475;
    		N1_2 = N1_2_AMR475;
    		N2_2 = N2_2_AMR475;
    		N1_2_coded = N1_2_coded_AMR475;
    		N2_2_coded = N2_2_coded_AMR475;
    		
                for (i=0; i<Fs_SpFrms_per_TDMFrm; i++)
                {
                  Fs_N0[i] = Fs_N0_AMR475[i];
                  Fs_N1[i] = Fs_N1_AMR475[i];
                  Fs_N2[i] = Fs_N2_AMR475[i];
                }
   		
                Fs_N0_Tot = Fs_N0_Tot_AMR475;
                Fs_N1_Tot = Fs_N1_Tot_AMR475;
                Fs_N2_Tot = Fs_N2_Tot_AMR475;
                Fs_N1_Tot_coded = Fs_N1_Tot_coded_AMR475;
    		Fs_N2_Tot_coded = Fs_N2_Tot_coded_AMR475;
    		
    		Length_vocoder_frame = Length_vocoder_frame_AMR475;
    		Length_2_frames = Length_2_frames_AMR475;
    		
    		SIZE_TAB_CRC1 = SIZE_TAB_CRC1_AMR475;
    		SIZE_TAB_CRC2 = SIZE_TAB_CRC2_AMR475;
    		SIZE_TAB_CRC3 = SIZE_TAB_CRC3_AMR475;
    		SIZE_TAB_CRC4 = SIZE_TAB_CRC4_AMR475;
    		SIZE_TAB_CRC5 = SIZE_TAB_CRC5_AMR475;
    		SIZE_TAB_CRC6 = SIZE_TAB_CRC6_AMR475;
    		SIZE_TAB_CRC7 = SIZE_TAB_CRC7_AMR475;
    		SIZE_TAB_CRC8 = SIZE_TAB_CRC8_AMR475;
    		
    		Fs_SIZE_TAB_CRC1 = Fs_SIZE_TAB_CRC1_AMR475;
    		Fs_SIZE_TAB_CRC2 = Fs_SIZE_TAB_CRC2_AMR475;
    		Fs_SIZE_TAB_CRC3 = Fs_SIZE_TAB_CRC3_AMR475;
    		Fs_SIZE_TAB_CRC4 = Fs_SIZE_TAB_CRC4_AMR475;

    		for (i=0; i<N0; i++)
    		  TAB0[i] = TAB0_AMR475[i];
    		for (i=0; i<N1; i++)
    		  TAB1[i] = TAB1_AMR475[i];
    		for (i=0; i<N2; i++)
    		  TAB2[i] = TAB2_AMR475[i];
    		
                for (j=0; j<Fs_SpFrms_per_TDMFrm; j++)
                {  
    		  for (i=0; i<Fs_N0[j]; i++)
    		    Fs_TAB0[j][i] = Fs_TAB0_AMR475[j][i];
    		  for (i=0; i<Fs_N1[j]; i++)
    		    Fs_TAB1[j][i] = Fs_TAB1_AMR475[j][i];
    		  for (i=0; i<Fs_N2[j]; i++)
    		    Fs_TAB2[j][i] = Fs_TAB2_AMR475[j][i];
    		}
    		  
    		for (i=0; i<Period_pct*3; i++)
    		{
    		  A1[i] = A1_AMR475[i];
    		  A2[i] = A2_AMR475[i];
    		  Fs_A1[i] = Fs_A1_AMR475[i];
    		  Fs_A2[i] = Fs_A2_AMR475[i];
    		}
    		
    		for (i=0; i<SIZE_TAB_CRC1; i++)
    		  TAB_CRC1[i] = ALLOW_NEG(TAB_CRC1_AMR475[i]);
    		for (i=0; i<SIZE_TAB_CRC2; i++)
    		  TAB_CRC2[i] = ALLOW_NEG(TAB_CRC2_AMR475[i]);
    		for (i=0; i<SIZE_TAB_CRC3; i++)
    		  TAB_CRC3[i] = ALLOW_NEG(TAB_CRC3_AMR475[i]);
    		for (i=0; i<SIZE_TAB_CRC4; i++)
    		  TAB_CRC4[i] = ALLOW_NEG(TAB_CRC4_AMR475[i]);
    		for (i=0; i<SIZE_TAB_CRC5; i++)
    		  TAB_CRC5[i] = ALLOW_NEG(TAB_CRC5_AMR475[i]);
    		for (i=0; i<SIZE_TAB_CRC6; i++)
    		  TAB_CRC6[i] = ALLOW_NEG(TAB_CRC6_AMR475[i]);
    		for (i=0; i<SIZE_TAB_CRC7; i++)
    		  TAB_CRC7[i] = ALLOW_NEG(TAB_CRC7_AMR475[i]);
    		for (i=0; i<SIZE_TAB_CRC8; i++)
    		  TAB_CRC8[i] = ALLOW_NEG(TAB_CRC8_AMR475[i]);


    		for (i=0; i<Fs_SIZE_TAB_CRC1; i++)
    		  Fs_TAB_CRC1[i] = ALLOW_NEG(Fs_TAB_CRC1_AMR475[i]);
    		for (i=0; i<Fs_SIZE_TAB_CRC2; i++)
    		  Fs_TAB_CRC2[i] = ALLOW_NEG(Fs_TAB_CRC2_AMR475[i]);
    		for (i=0; i<Fs_SIZE_TAB_CRC3; i++)
    		  Fs_TAB_CRC3[i] = ALLOW_NEG(Fs_TAB_CRC3_AMR475[i]);
    		for (i=0; i<Fs_SIZE_TAB_CRC4; i++)
    		  Fs_TAB_CRC4[i] = ALLOW_NEG(Fs_TAB_CRC4_AMR475[i]);                

                Fs_Fixed_Bits[0] = Fs_Fixed_Bits_AMR475[0];
                Fs_Fixed_Bits[1] = Fs_Fixed_Bits_AMR475[1];
      
                for (i=j=0; i<Fs_Fixed_Bits[0]; i++,j++)
                {
                  Fs_Fixed_Bit_TAB[0][i] = Fs_Fixed_Bit_TAB_AMR475[0][i];
                  Fs_Fixed_Bit_List[j] = Fs_Fixed_Bit_List_AMR475[j];
                }
                for (i=0; i<Fs_Fixed_Bits[1]; i++,j++)
                {
                  Fs_Fixed_Bit_TAB[1][i] = Fs_Fixed_Bit_TAB_AMR475[1][i];
                  Fs_Fixed_Bit_List[j] = Fs_Fixed_Bit_List_AMR475[j];
                }

//                printf("Fs_N0_Tot = %d, Fs_N1_Tot = %d, Fs_N2_Tot = %d\n",Fs_N0_Tot,Fs_N1_Tot,Fs_N2_Tot);
//                printf("Fs_N1_Tot_coded = %d, Fs_N2_Tot_coded = %d\n",Fs_N1_Tot_coded, Fs_N2_Tot_coded);                
                
//                printf("Fs_TAB0[j][i] = ");   
//                for (j=0; j<Fs_SpFrms_per_TDMFrm; j++)
//    		  for (i=0; i<Fs_N0[j]; i++)
//    		    printf("%d, ",Fs_TAB0[j][i]);

//                printf("\nFs_TAB1[j][i] = ");   
//                for (j=0; j<Fs_SpFrms_per_TDMFrm; j++)
//    		  for (i=0; i<Fs_N1[j]; i++)
//    		    printf("%d, ",Fs_TAB1[j][i]);

//                printf("\nFs_TAB2[j][i] = ");   
//                for (j=0; j<Fs_SpFrms_per_TDMFrm; j++)
//    		  for (i=0; i<Fs_N2[j]; i++)
//   		    printf("%d, ",Fs_TAB2[j][i]);
//                printf("\n");   

     		break;

    default:	SpFrms_per_TDMFrm = 2;
                Fs_SpFrms_per_TDMFrm = 1;
    
    		N0 = N0_TETRA;
    		N1 = N1_TETRA;
    		N2 = N2_TETRA;
    		N0_2 = N0_2_TETRA;
    		N1_2 = N1_2_TETRA;
    		N2_2 = N2_2_TETRA;
    		N1_2_coded = N1_2_coded_TETRA;
    		N2_2_coded = N2_2_coded_TETRA;

                Fs_N0[0] = N0_TETRA;
                Fs_N1[0] = N1_TETRA;
                Fs_N2[0] = N2_TETRA;
   		
                Fs_N0_Tot = Fs_N0_Tot_TETRA;
                Fs_N1_Tot = Fs_N1_Tot_TETRA;
                Fs_N2_Tot = Fs_N2_Tot_TETRA;
                Fs_N1_Tot_coded = Fs_N1_Tot_coded_TETRA;
    		Fs_N2_Tot_coded = Fs_N2_Tot_coded_TETRA;

    		Length_vocoder_frame = Length_vocoder_frame_TETRA;
    		Length_2_frames = Length_2_frames_TETRA;
    		
    		SIZE_TAB_CRC1 = SIZE_TAB_CRC1_TETRA;
    		SIZE_TAB_CRC2 = SIZE_TAB_CRC2_TETRA;
    		SIZE_TAB_CRC3 = SIZE_TAB_CRC3_TETRA;
    		SIZE_TAB_CRC4 = SIZE_TAB_CRC4_TETRA;
    		SIZE_TAB_CRC5 = SIZE_TAB_CRC5_TETRA;
    		SIZE_TAB_CRC6 = SIZE_TAB_CRC6_TETRA;
    		SIZE_TAB_CRC7 = SIZE_TAB_CRC7_TETRA;
    		SIZE_TAB_CRC8 = SIZE_TAB_CRC8_TETRA;
    		
    		Fs_SIZE_TAB_CRC1 = Fs_SIZE_TAB_CRC1_TETRA;
    		Fs_SIZE_TAB_CRC2 = Fs_SIZE_TAB_CRC2_TETRA;
    		Fs_SIZE_TAB_CRC3 = Fs_SIZE_TAB_CRC3_TETRA;
    		Fs_SIZE_TAB_CRC4 = Fs_SIZE_TAB_CRC4_TETRA;

    		for (i=0; i<N0; i++)
    		  TAB0[i] = TAB0_TETRA[i];
    		for (i=0; i<N1; i++)
    		  TAB1[i] = TAB1_TETRA[i];
    		for (i=0; i<N2; i++)
    		  TAB2[i] = TAB2_TETRA[i];
    		  
    		for (i=0; i<N0; i++)
    		  Fs_TAB0[0][i] = TAB0_TETRA[i];
    		for (i=0; i<N1; i++)
    		  Fs_TAB1[0][i] = TAB1_TETRA[i];
    		for (i=0; i<N2; i++)
    		  Fs_TAB2[0][i] = TAB2_TETRA[i];
    		  
    		for (i=0; i<Period_pct*3; i++)
    		{
    		  A1[i] = A1_TETRA[i];
    		  A2[i] = A2_TETRA[i];
    		  Fs_A1[i] = Fs_A1_TETRA[i];
    		  Fs_A2[i] = Fs_A2_TETRA[i];
    		}
    		
    		for (i=0; i<SIZE_TAB_CRC1; i++)
    		  TAB_CRC1[i] = ALLOW_NEG(TAB_CRC1_TETRA[i]);
    		for (i=0; i<SIZE_TAB_CRC2; i++)
    		  TAB_CRC2[i] = ALLOW_NEG(TAB_CRC2_TETRA[i]);
    		for (i=0; i<SIZE_TAB_CRC3; i++)
    		  TAB_CRC3[i] = ALLOW_NEG(TAB_CRC3_TETRA[i]);
    		for (i=0; i<SIZE_TAB_CRC4; i++)
    		  TAB_CRC4[i] = ALLOW_NEG(TAB_CRC4_TETRA[i]);
    		for (i=0; i<SIZE_TAB_CRC5; i++)
    		  TAB_CRC5[i] = ALLOW_NEG(TAB_CRC5_TETRA[i]);
    		for (i=0; i<SIZE_TAB_CRC6; i++)
    		  TAB_CRC6[i] = ALLOW_NEG(TAB_CRC6_TETRA[i]);
    		for (i=0; i<SIZE_TAB_CRC7; i++)
    		  TAB_CRC7[i] = ALLOW_NEG(TAB_CRC7_TETRA[i]);
    		for (i=0; i<SIZE_TAB_CRC8; i++)
    		  TAB_CRC8[i] = ALLOW_NEG(TAB_CRC8_TETRA[i]);
    		
    		for (i=0; i<Fs_SIZE_TAB_CRC1; i++)
    		  Fs_TAB_CRC1[i] = ALLOW_NEG(Fs_TAB_CRC1_TETRA[i]);
    		for (i=0; i<Fs_SIZE_TAB_CRC2; i++)
    		  Fs_TAB_CRC2[i] = ALLOW_NEG(Fs_TAB_CRC2_TETRA[i]);
    		for (i=0; i<Fs_SIZE_TAB_CRC3; i++)
    		  Fs_TAB_CRC3[i] = ALLOW_NEG(Fs_TAB_CRC3_TETRA[i]);
    		for (i=0; i<Fs_SIZE_TAB_CRC4; i++)
    		  Fs_TAB_CRC4[i] = ALLOW_NEG(Fs_TAB_CRC4_TETRA[i]);

                Fs_Fixed_Bits[0] = 0;

    		break;
  }
}
