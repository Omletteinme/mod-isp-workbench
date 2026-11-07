# MetaISPNet extracted from the upstream MIT-licensed metaisp_model.py.
# Only the inference network is needed; training wrappers require CUDA-only PWC.
import torch
import torch.nn as nn
from functools import partial
from . import networks as N
from . import attention_models

class MetaISPNet(nn.Module):
    def __init__(self, opt):
        super(MetaISPNet, self).__init__()

        self.opt = opt

        #Global Feature Extractor
        self.xcit = attention_models.XCiT(patch_size=16, embed_dim=128, depth=4, num_heads=4, mlp_ratio=4, qkv_bias=True,
                            norm_layer=partial(nn.LayerNorm, eps=1e-6), eta=1.0, tokens_norm=False)
       
        #Illutmination Estimation
        if opt.illuminant:
            self.illumination = Illumination()

        #Iso and Exposure mixture and projection
        if self.opt.iso_exp:
            self.IsoExp = IsoExp()

        # White Balance Projection
        self.color_scaler_lv_0 = nn.Conv2d(4, 4, 1, 1, 0)
        self.color_scaler_lv_1 = nn.Conv2d(4, 64, 1, 1, 0)

        ch_1 = 64
        ch_2 = 128
        
        self.multi_device = opt.multi_device
        self.query_emb = opt.query_emb

        if opt.multi_device:
            self.emb = nn.Embedding(3, 128)
            self.emb_lv1 = nn.Conv2d(128, 512, 1, 1, 0, bias=True, padding_mode='zeros')

            if self.opt.illuminant:
                self.emb_4 =  nn.Conv2d(128, 64, 1, 1, 0, bias=True, padding_mode='zeros')

        self.emb_ada_up3 =  nn.Conv2d(128, ch_2, 1, 1, 0, bias=True, padding_mode='zeros') 
        self.emb_ada_up2 =  nn.Conv2d(128, ch_1, 1, 1, 0, bias=True, padding_mode='zeros') 
        self.emb_ada_up1 =  nn.Conv2d(128, ch_1, 1, 1, 0, bias=True, padding_mode='zeros') 
            
        
        self.pre_ispnet_coord = opt.pre_ispnet_coord

        attention_layer = self.opt.attention
        attention_match = self.opt.attention_match

        self.head = N.seq(
            N.conv(4, ch_1, mode='C')
            ) 

        self.down1_0 = N.conv(ch_1+2, ch_1+2, mode='C')
        self.down1_1 = N.RCAGroup(in_channels=ch_1+2, out_channels=ch_1+2,  depth=opt.depth, heads=2, attention=attention_layer,attention_match=attention_match,
                        positional=opt.positional)
        self.down1_2 = N.conv(ch_1+2, ch_1, mode='C')
        self.down1_3 = N.DWTForward(ch_1)


        self.down2_0 = N.conv(ch_1*4, ch_1, mode='C')
        self.down2_1 = N.RCAGroup(in_channels=ch_1, out_channels=ch_1,  depth=opt.depth, heads=4, attention=attention_layer,attention_match=attention_match,
                       positional=opt.positional)
        self.down2_2 = N.DWTForward(ch_1)


        self.down3_0 = N.conv(ch_1*4, ch_2, mode='C')
        self.down3_1 = N.RCAGroup(in_channels=ch_2, out_channels=ch_2,  depth=opt.depth, heads=4, attention='off',attention_match=attention_match,
                        positional=opt.positional)
        self.down3_2 = N.DWTForward(ch_2)


        self.middle_conv1 = N.conv(ch_2*4, ch_2, mode='C')
        self.middle_group1 = N.RCAGroup(in_channels=ch_2, out_channels=ch_2,  depth=opt.depth, heads=4, attention='off',attention_match=attention_match,
                                        positional=opt.positional)
        self.middle_group2 = N.RCAGroup(in_channels=ch_2, out_channels=ch_2,  depth=opt.depth, heads=4, attention='off',attention_match=attention_match,
                                        positional=opt.positional)
        self.middle_conv2 = N.conv(ch_2, ch_2*4, mode='C')
        
        if  self.query_emb:
            self.up3_up = N.DWTInverse(ch_2*4)
            self.up3_att = N.RCAGroup(in_channels=ch_2, out_channels=ch_2,  depth=opt.depth, heads=4, attention='off',attention_match=attention_match,
                                positional=opt.positional, adain=ch_2)
            self.up3_conv = N.conv(ch_2, ch_1*4, mode='C')


            self.up2_up = N.DWTInverse(ch_1*4)
            self.up2_att = N.RCAGroup(in_channels=ch_1, out_channels=ch_1,  depth=opt.depth, heads=4, attention=attention_layer,attention_match=attention_match,
                            positional=opt.positional, adain=ch_1)
            self.up2_conv = N.conv(ch_1, ch_1*4, mode='C')


            self.up1_up = N.DWTInverse(ch_1*4)
            self.up1_att = N.RCAGroup(in_channels=ch_1, out_channels=ch_1,  depth=opt.depth, heads=4, attention=attention_layer,attention_match=attention_match,
                            positional=opt.positional, adain=ch_1)
            self.up1_conv = N.conv(ch_1, ch_1, mode='C')

        self.tail = N.seq(
            N.conv(ch_1, ch_1*4, mode='C'),
            nn.PixelShuffle(upscale_factor=2),
            N.conv(ch_1, 3, mode='C')
            )  # shape: (N, 3, H, W)   

    def forward(self, raw, raw_full, color_scaler=None, coord=None, mobile_id=0, latent=False, coords=None, exp=None, iso=None):
        #Gamma correction
        input = torch.pow(raw, 1/2.2)

        if self.multi_device:
            if latent:
                results = []
                vectors = list()
                embedding_iphone = torch.unsqueeze(torch.unsqueeze(self.emb(torch.tensor([2]).to(raw.device)),2),2)
                embedding_samsung = torch.unsqueeze(torch.unsqueeze(self.emb(torch.tensor([1]).to(raw.device)),2),2)
                embedding_pixel = torch.unsqueeze(torch.unsqueeze(self.emb(torch.tensor([0]).to(raw.device)),2),2)

                ratios = torch.linspace(0, 1, self.opt.latent_n)

                for ratio in ratios:
                    v = (1.0 - ratio) * embedding_iphone + ratio * embedding_pixel
                    vectors.append(v)

                for ratio in ratios:
                    v = (1.0 - ratio) * embedding_pixel + ratio * embedding_samsung
                    vectors.append(v)

                batch_size_inter = self.opt.latent_n
                b = torch.Tensor(batch_size_inter*2, 128, 1, 1).to(raw.device)
                torch.cat(vectors, out=b)
                embedding = b
                
                emb_bottleneck = self.emb_lv1(b)
            else:

                embedding = torch.unsqueeze(torch.unsqueeze(self.emb(mobile_id),2),2)
                emb_bottleneck = self.emb_lv1(embedding)
        
        if self.opt.illuminant:
            color_scaler = self.illumination(input,self.emb_4(embedding))

        features = self.xcit(raw_full)

        color_scaler_0 = self.color_scaler_lv_0(color_scaler)
        color_scaler_64 = self.color_scaler_lv_1(color_scaler_0)

        if latent:
            for i in range(self.opt.latent_n*2):
                if self.opt.iso_exp:
                    raw_p = self.IsoExp(exp.unsqueeze(1).float(),iso.unsqueeze(1).float(),input*color_scaler_0)
                    h = self.head(raw_p)
                else:
                    h = self.head(input*color_scaler_0)

                h_coord = torch.cat((h*color_scaler_64, coord), 1)

                d1 = self.down1_0(h_coord)
                d1 = self.down1_1(d1,coords=coords)
                d1 = self.down1_2(d1)
                d1 = self.down1_3(d1)

                d2 = self.down2_0(d1)
                d2 = self.down2_1(d2,coords=coords)
                d2 = self.down2_2(d2)

                d3 = self.down3_0(d2)
                d3 = self.down3_1(d3,coords=coords)
                d3 = self.down3_2(d3)


                #Bottleneck
                g = self.middle_conv1(d3) 
                g = self.middle_group1(g,coords=coords)
                g = self.middle_group2(g,coords=coords)
                m = (self.middle_conv2(g) + d3)*emb_bottleneck[i].unsqueeze(0)

                #Global Features
                m = m*features

                #Decoding
                if self.query_emb:

                    emb_u3 = self.emb_ada_up3(embedding[i].unsqueeze(0)) 
                    emb_u2 = self.emb_ada_up2(embedding[i].unsqueeze(0))
                    emb_u1 = self.emb_ada_up1(embedding[i].unsqueeze(0))

                    u3 = self.up3_up(m)
                    u3 = self.up3_att(u3,emb_u3,coords=coords)
                    u3 = self.up3_conv(u3) + d2 

                    u2 = self.up2_up(u3)
                    u2 = self.up2_att(u2,emb_u2,coords=coords)
                    u2 = self.up2_conv(u2) + d1

                    u1 = self.up1_up(u2)
                    u1 = self.up1_att(u1,emb_u1,coords=coords)
                    u1 = self.up1_conv(u1) + h  
            
                    out = self.tail(u1)
                else:
                    u3 = self.up3(m) + d2
                    u2 = self.up2(u3) + d1
                    u1 = self.up1(u2) + h
                    out = self.tail(u1)

                results.append(out)

            return results

        else:
            
            if self.opt.iso_exp:
                raw_p = self.IsoExp(exp.unsqueeze(1).float(),iso.unsqueeze(1).float(),input*color_scaler_0)
                h = self.head(raw_p)
            else:
                h = self.head(input*color_scaler_0)

            h_coord = torch.cat((h*color_scaler_64, coord), 1)


            if self.multi_device:

                #Encoding
                d1 = self.down1_0(h_coord)
                #print(coords.shape)
                d1 = self.down1_1(d1,coords=coords)
                d1 = self.down1_2(d1)
                d1 = self.down1_3(d1)

                d2 = self.down2_0(d1)
                d2 = self.down2_1(d2,coords=coords)
                d2 = self.down2_2(d2)

                d3 = self.down3_0(d2)
                d3 = self.down3_1(d3,coords=coords)
                d3 = self.down3_2(d3)


                #Bottleneck
                g = self.middle_conv1(d3) 
                g = self.middle_group1(g,coords=coords)
                g = self.middle_group2(g,coords=coords)
                m = (self.middle_conv2(g) + d3)*emb_bottleneck

                #Global Features
                m = m*features

                #Decoding
                if self.query_emb:

                    emb_u3 = self.emb_ada_up3(embedding) 
                    emb_u2 = self.emb_ada_up2(embedding)
                    emb_u1 = self.emb_ada_up1(embedding)

                    u3 = self.up3_up(m)
                    u3 = self.up3_att(u3,emb_u3,coords=coords)
                    u3 = self.up3_conv(u3) + d2 

                    u2 = self.up2_up(u3)
                    u2 = self.up2_att(u2,emb_u2,coords=coords)
                    u2 = self.up2_conv(u2) + d1

                    u1 = self.up1_up(u2)
                    u1 = self.up1_att(u1,emb_u1,coords=coords)
                    u1 = self.up1_conv(u1) + h  
            
                    out = self.tail(u1)

                else:
                    u3 = self.up3(m) + d2
                    u2 = self.up2(u3) + d1
                    u1 = self.up1(u2) + h
                    out = self.tail(u1)
                
                if  self.opt.illuminant:
                    return out, color_scaler
                else:
                    return out

            else:
                d1 = self.down1(h_coord)
                d2 = self.down2(d1)
                d3 = self.down3(d2)
                m = self.middle_conv1(d3) 
                m = self.middle_group1(m)
                m = self.middle_group2(m)
                m = self.middle_conv2(m) + d3
                #m = self.middle(d3) + d3
                u3 = self.up3(m*features) + d2
                u2 = self.up2(u3) + d1
                u1 = self.up1(u2) + h
                out = self.tail(u1)

                if  self.opt.illuminant:
                    return out, color_scaler
                else:
                    return out
                    
